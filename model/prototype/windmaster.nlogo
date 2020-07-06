__includes [ "utilities.nls" "setup.nls" "decisionMakingModels.nls" ] ; all the boring but important stuff not related to content
extensions [ csv py ]

;TODO
; Zorgen dat havenzijdig H2 import uit technisch model wordt gehaald
; reporter op het einde, timeseries afleveren, list of floats, index is jaar/tick
; event is [assedIT, aset type, asset type technology, year, volume]
; volume of -1 = not relevant
; technology type -1 = remove




globals [
  ; varibales for the map
  topleftx
  toplefty
  bottomrightx
  bottomrighty
  energyCarrierNames
  possibleAssetStatuses
  labelStatus
  existingConversionAssets
  existingConnectonLinks
  possibleStatusList
  allMarkets ; agentset that holds all the market conversionAssets
  marketNames ; defines which markets exist [AssetID, capacity, year]
  selectedAsset ; the selected asset for all sorts of GUI interactions
  xlist
  stedinsLostCustomersList ; list of customers that stedin lost
                           ;decisionMakingModel ; which decision making model is used, defined in the chooser:  "Reactive", "Current", "Proactive", "Collaborative"
  decisionMaking ; convenience variable, so that we can use it as index for all sorts of lists
  year ; which year is it?
  elapsedYears ; years that have been simulated

  investmentData ; the list of list, holding the investment descriptions
                 ; InvestID,CAPEX_Meuro,Leadtimereactive_year,Leadtimecurrent_year,Leadtimeproactive_year,Leadtimecollaborative_year,Owner,Investtype,Capacityinvestmentbuildingblock_MW,Opmerking,,
  investmentIdList ; the list of investmentIDs, from ivnestment Data

  investmentHistory ; a global list, in which each asset owner records  [which asset owner, identifier of what is invested, in which year, capex investment]
  portsideH2History ; all of the portside imports of H2, per year

  ;convenience turtle references
  stedin
  tennet
  gts
  hbr
  pzh
  activeInfraProviders ; pzh, hbr are not active, but will have other roles
  collaborativeInfraProvider ; the one big infra provider

  ;from EMA
  scenario ; scenario is a list of lists [[assset ID, assetTypeIndex, assetTechnologyTypeIndex,year]] ; defines replacement/upgrade of existing assets
  scenarioEventsThatCouldNotBeAccomodated ; a lit of scenario events that could not happen because of insufficient  the infrastructure
  yearGunvorPhaseout
  yearKochPhaseout
  yearBPOffline
  yearHydrocrackerBP
  ;  havenzijdige H2 import


  ;  In welk jaar, is welke event niet gebeurt, door gebrek aan welke infra, en met hoeveel MW tekort
  ;  per jaar, hoeveel capx uitgegeven per infra beheerder

  realisedScenarioEvents

  ;1 - Percentage waargemaakte transitiepaden per beleidsoptie
  ; retrn to EMA :
  ; the scenario -> sequence of evens that has happened
  ; list of events that has occured with status True, list of list, use reportScenario procedure, as EMA needs a list of stings, and can not handle a list of list being sent back
  ;  this allows ema  to compute the fraction of events that happened
  ; per scenario return :
  ;  -list of CO2 emissions deltas of each event would have happened -> original scenario with associated CO2 deltas
  ; - a list of actual CO2 deltas that happened as consequence of associate event that was implemented - actual event list with CO2 delta

  considerRuningInvestments? ; a global controlling whether infrastructure providers consider running investments

]


breed [conversionAssets conversionAsset]
directed-link-breed [connectionLinks connectionLink]
breed[infraProviders infraProvider]


infraProviders-own[
  ownedConversionAssets ; all of my conversionAssets
  ownedConnectionLinks ; all of my connectionLinks
                       ;ownedAssets ; all of my assets -netlogo does not like mixing turtles and links in one agentset
  name
  yearlyBudget ; the budget we recieve this year [x y z p] based on decision making
  budget ; current budget
  neededInvestmentsWithinExpectedDemand ; list of list, describing which infrastructure investments are needed to deal with the expected demand
                                        ; list of list [[investmentID, owner name, MW additional overcapacity that the investment generates,  MEUR CAPEX, year when it will be finished, amount, investmentSetId, investmentAlernativeId ] [...] [...] ]
  investmentsCurrentlyUnderConstruction ; list of investments that are currently being developed

  timeHorizon ; list of decisionMakingModel dependent number of years a infrarovider can see into the future of the current scenario, and conders any other time dependent logic
  demandExpectations ; a list of scenario events that we expect to hapen
  stateOfTheGrid ; A list of list,[ ["totalMaxMW capacity"  "total MWs flowing in the system" "year"]] where the state of the infrastrcuture owned by this provider is stored. It will be read at the end of simulation by EMA
  myInfrastructureInvestments ; the list of lists

  ;decision making convenience variables
  ; we recieve from technical model investments structured as : optionSet ( option (investmentSet (investment)))
  ; option set -> the discrete investmnets taht need to be made
  ; option -> a colection of nvetment sets that are available for this investment
  ; investmentSet -> an investment can consists of 1 or more investpents in a speciffic assetID

  investmentSetIDs  ; All unique investmetnSetIds
  investmentSets ; one of more discrete Investments that for a solution to the given demand  problem

  optionSetIDs ;
  optionSets ; a collection of investmentSet options that are equivalent in technically solving the demand problem
  capex_factor
  leadtime_factor
  shuffle-needed-investments?



]


conversionAssets-own [
  ;internal variablesrealisedScenarioEvents
  xmap ; for storing original location, so that we can mess with animated locations
  ymap

  name ; a string let name (sentence "conversionAsset " label " with id " assetID "from row " fromDataRow)
  dataRow ; the row the asset comes from
          ; Variables from the conversion assets data file
  clusterID ;  Site's location within industrial cluster ["MV_A", "MV_B", "EUR_A","EUR_B","EUR_C","BOT_A","BOT_B","PER"]
  siteID ;  "Site ID [String, no spaces] – must be unique"
  assetID ; "Conversion asset ID [string, without spaces] – Must be unique"
  status ; "Asset status (existing/   considered for construction/ planned for construction/ under construction / considered for decommissioning/planned for decommissioning/under decommissioning"
  alternativeFor ;"Alternative for  asset (asset ID/UNDEF/0) IF 0 than completely new asset on site"
  periodConsideredForConstruction ;"Period option can be considered for construction (start year:end year)"
  durationOfConstruction;  duration of construction, once started, year
  periodConsideredForDecomisioning ;  Period option can be considered for disinvestment (start year:end year)
  durationOfDecomissioning ;  Duraction of decomissioning, [years]
  xlocation ;  X (center of site) ESRI coordinates
  ylocation ;  Y (center of site)
  humanReadableName ;will be mapped to  label ;  "Asset description –  human readable form – [String, no commas]"
  assetOwner ;  "Owner – must be unique {String]"
  feedstocks ;  "Feedstocks  of conversion assets– list of product names
  feedstockAmounts ; How many MW of feedstock enters the conversion asset, list in same order as feedstock energy carrier names
  conversionEfficiencyToElectricity ;  "Conversion efficiency to electricity [fraction], a list of numbers separated by : in the same order as the feedstocks field"
  conversionEfficiencyToSteam ;  "Conversion efficiency to steam [fraction], , a list of numbers separated by : in the same order as the feedstocks field"
  conversionEfficiencyToHTheat ;  "Conversion efficiency to HT heat [fraction], , a list of numbers separated by : in the same order as the feedstocks field"
  conversionEfficiencyToLTheat ;  "Conversion efficiency to LT heat [fraction], , a list of numbers separated by : in the same order as the feedstocks field"
  conversionEfficiencyToH2;  "Conversion efficiency to H2 [fraction], , a list of numbers separated by : in the same order as the feedstocks field"
  conversionEfficiencyToNatgas
  utilization ; "Utilization @ max. capacity [fraction of time], of conversion asset"
  CO2EmissionFactor ;  "CO2 emission factor of conversion asset [list of factors per feedstock type],
  linesToAsset ;  Incoming lines to this conversion asset, list of unique lineIDs separated by :" NULL if none
  linesFromAsset; Outoging lines from conversion asset, list of unique lineIDs names, separated by :, NULL if none
  assetCapex ;"CAPEX (UNDEF / cost)"
]


connectionLinks-own[
  lineID ;"Line ID unique [string]"
  fromAsset ;"From – conversion asset – unique [sting]"
  toAsset ;"To – conversion asset – unique [sting]"
  feedstock ;"Feedstock carried"
  maxCapacity;"Maximum capacity link [MW]"
             ;"Current max. capacity utilisation [MW]"
             ;"Internal lines (yes/no = true/false)"
             ;"transport / connection "
  lineOwner;"Owner"
  lineCapex;"CAPEX"

]


;stedin

;Bepaalt wat de aankomende aanbod/vraag mix is afhankelijk van hoever Stedin vooruit kijkt
;Verzamelt lijst van assets die gegeven de aankomende vraag/aanbod overbelast zouden zijn maximale capaciteit van de asset wordt overschreden
;Gaat investeren in netuitbreiding/verzwaring Als er een directe aanvraag ligt
;Als Stedin investeert, kijkt men naar de potentie voor komende 10 jaar (Potentie = ik investeer 30% meer dan nodig, als ik 30% groei verwacht) Pro-actief gedrag
;Verwachting (gebiedsanalyse) = verzamelen van informatie over aankomende aanvragen van andere infra providers
;Weigert  / accepteert accomoderen vraag/aanbod nu direct ( binnen 1 jaar) Beschikbare capacitieit op het netwerk op een specifieke locatie (verwerking binnen 26 weken, als er plek is wel aansluiten, anders klant moet betalen voor de kabel)
;Geweigerde aanvragen worden onthouden. Deze worden later opnieuw in overweging meegenomen voor uitbreiding. vooral onder de reactieve gedrags model
;Investeert in een asset Afhankelijk van grootte van de aanvraag ( 10 huizen niet, BP raffinaderij wel)
;Uitbreidingen gaat in blokken van resp. 40, 80,  160 MVA


to go
  setYear ; set the current year. We start in 2020
  if debug? [
    debug (word "------------------------ Year: " year " ------------------------------------------------------")


]

  ;how will I decide which investment to do, dependent on the decision making model
  if decisionMakingModel = "Reactive" [
    reactiveDecisionMakingModel
  ]

  if decisionMakingModel = "Current" [
    currentDecisionMakingModel
  ]

  if decisionMakingModel = "Proactive" [
    proactiveDecisionMakingModel
  ]

  if decisionMakingModel = "Collaborative" [
    collaborativeDecisionMakingModel
  ]

  ;here we shange all demand/supply assets as per scenario. Each change recieves either true/false depending whehter it could be supported byt he infrastructure
  changePhysicalWorld

  performMetricsGathering

  tick ; next time step
end

to processScenarioEvents
  ;in this procedure all other evendemandExpectationsts that are set as categorical variables are added to scenario list,
  ;  yearGunvorPhaseout
  ;  yearKochPhaseout
  ;  yearBPOffline
  ;  yearHydrocrackerBP
  ;
  ; removal of assets  are scenario elements with [[assset ID, -1, -1,year]]
  if yearGunvorPhaseout != 0 [ ; phaseout is happening
    let gunvorAssets [assetID] of conversionAssets with [assetOwner = "Gunvor"]
    foreach gunvorAssets [asset ->
      set scenario lput (list asset -1 -1 yearGunvorPhaseout 0) scenario
    ]

    if yearKochPhaseout != 0 []
    let kochAssets [assetID] of conversionAssets with [assetOwner = "Koch"]
    foreach  kochAssets [ asset ->
      set scenario lput (list asset -1 -1 yearKochPhaseout 0) scenario
    ]
  ]

  if YearBPOffline != 0 [
    ;TODO
    ; Alles wat owner BP heeft gaat dood.
    let bpAssets [assetID] of conversionAssets with [assetOwner = "BP"]
    foreach  bpAssets [ asset ->
      set scenario lput (list asset -1 -1 yearBPOffline 0) scenario
    ]
  ]

  if yearHydrocrackerBP != 0 [
    ;TODO
    ;    d4 ; colomn P
    ;    115:120:453:130:74:278:79:159:13
    ;    laatste twee 159:13 = 172 dat is H2 vraag
    ;    met hydrocracker er bij, H2 gaat omhoog met 420MW zoveel
    ; TODO this needs events die vervanging zijn, die anders is dan technology paths

  ]
end

to changePhysicalWorld

  ;here we change all demand/supply assets as per scenario. Each change recieves either true/false depending whether it could be supported by the infrastructure

  let eventsThisYear filter [event -> item 3 event = year] scenario ;

  foreach eventsThisYear [event ->
    ;remove assets
    ifelse item 1 event = -1 AND item 2 event = -1 [
      let asset item 0 event
      if py:runresult (word "model.removeAsset(\"" asset "\")") [
        set realisedScenarioEvents lput event realisedScenarioEvents
      ]
    ]
    [ ; else, if we are not removing assets
      ;let message (word "\""  item 0 event  "\"," item 1 event "," item 2 event )
      py:set "event" event
      if py:runresult "model.changeAsset(event)"  [
        set realisedScenarioEvents lput event realisedScenarioEvents
      ]
    ]
  ]
  ;debug (word "Scenario events are : " scenario)
  ;debug (word "Realised scenario events are : " realisedScenarioEvents)

end

;; Reporters for EMA testing


to-report numberOfScenarioEventsPerYear
  let listOfEventsPerYear []
  let knownYears  n-values (30)  [y -> 2020  + y]

  foreach knownYears [ y ->
    let eventsThisYear length filter [event -> item 3 event = y] scenario
    set listOfEventsPerYear lput eventsThisYear listOfEventsPerYear
  ]


  report listOfEventsPerYear
end

to-report reportScenario
  report reformatedListOfEvents scenario

end

to-report reportRealisedScenarioEvents
  report reformatedListOfEvents realisedScenarioEvents
end

to-report reportScenario_2
  report scenario
end

to-report stedinCapacityAndLoadOverTime
  report [stateOfTheGrid] of stedin
end

to-report tennetCapacityAndLoadOverTime
  report [stateOfTheGrid] of tennet
end

to-report gtsCapacityAndLoadOverTime
  report [stateOfTheGrid] of gts
end

to-report investmentsOverTime
  ; this reporter is run by EMA at the end of the run


  let ivestmentsOverviewTable [] ;  as long as there are simulated years, items long ( 2020 ->2050), witdh as many columns as many investmentIDs there are, per index, an integer of how many times that investment ID has occured that year
  ;show investmentHistory
  let numberOfColumns length investmentData ; as many rolumns as many rows in investmetn table
  foreach elapsedYears [yearExamined ->

    let rowToReport n-values numberOfColumns [0] ; make the row of the right width, with 0s in it. then we will start replacing items
    ;[investmentID, owner, MW additional capacity that the investment generates,  MEUR CAPEX, year when it will be finished, insvestmentSetID, optionId,..........<allerlei dingen die jan in technisch model instopt ....,  agentMaking the Investment, year investment was made ]
    let investmentsThisYear filter  [inv -> last inv = yearExamined] investmentHistory ; all investments that happened in the examined year
    foreach investmentsThisYear [ investment ->

      let investmentID item (length investment - 4) investment ; we get the 3rd last item, the investmentId
      let investmentIndex position investmentID investmentIdList

      ;replace-item index list value
      set rowToReport replace-item investmentIndex rowToReport (item investmentIndex rowToReport + 1) ;add 1 to the number at this location. effectively couting each type
    ]
   set ivestmentsOverviewTable lput rowToReport ivestmentsOverviewTable
  ]; end foreach elapsed year




  report ivestmentsOverviewTable
end

to-report capexOverTime
  ; CAPEX ontwikkeling infra per beleidsoptie
  ; report a list of capexs spent on infra investments per year
  ; [stedin, TenneT, GTS, Collaborative], per row one year, per column the capex spend this year
  let capexOverviewTable []
  let infraprovidersList  ["Stedin" "TenneT" "GTS" "Collaborative"]

  foreach elapsedYears [yearExamined ->
    let rowToReport n-values length infraprovidersList [0] ; make the row of the right width, with 0s in it. then we will start replacing items
    let investmentsThisYear filter  [inv -> last inv = yearExamined] investmentHistory ; all investments that happened in the examined year.
    ;The final field is the year, as it is appended to the investment object in the makeInfrastructureInvestment
    foreach investmentsThisYear [ investment ->
      ;[investmentID, owner, MW additional capacity that the investment generates,  MEUR CAPEX, year when it will be finished, insvestmentSetID, optionId,..........<allerlei dingen die jan in technisch model instopt ....,  agentMaking the Investment, year investment was made ]

      let ownerIndexInInvestmentList (length investment - 2)
      ;debug (word " capex calculation - ownerIndexInInvestmentList :" ownerIndexInInvestmentList)
      let owner item ownerIndexInInvestmentList investment ; we dont want the second fiels in investments,  becuase we might get it wrong with cllaborative
      let ownerIndex position owner infraprovidersList ; this is the index in the infra provider list
      let capex item 3 investment

      ;replace-item index list value
      set rowToReport replace-item ownerIndex rowToReport capex ;
    ]
   set capexOverviewTable lput rowToReport capexOverviewTable
  ]; end foreach elapsed year

  report capexOverviewTable
end


to performMetricsGathering
  ; ["totalMaxMW capacity"  "total MWs flowing in the system" "year"]
  ask activeInfraProviders [
    set stateOfTheGrid lput py:runresult (word "model.getCurrentInfrastructureStatus('"name"')") stateOfTheGrid
  ]
  set elapsedYears lput year elapsedYears ; add the current year to the list of simulated years

  let x stedinsLostCustomersThisYear ; trigger the reportr, that also updtes the list, so that the end of run reporter can also be used

  set portsideH2History lput py:runresult "model.determineImportExportGas()"  portsideH2History
end

to-report stedinsLostCustomers

  let eventsPerYear []
  foreach stedinsLostCustomersList [ events ->
    set eventsPerYear lput length events eventsPerYear

  ]

  report eventsPerYear
end

to-report portsideH2OverYears
  report portsideH2History
end
to-report stedinsLostCustomersThisYear
  let thisYear py:runresult "model.stedinsLostCustomersThisYear()"
  set stedinsLostCustomersList lput thisYear stedinsLostCustomersList

  report thisYear
end
@#$#@#$#@
GRAPHICS-WINDOW
180
10
1565
657
-1
-1
0.5
1
10
1
1
1
0
0
0
1
0
1384
0
637
0
0
1
ticks
30.0

BUTTON
11
25
84
58
NIL
setup
NIL
1
T
OBSERVER
NIL
S
NIL
NIL
1

OUTPUT
47
670
1841
876
12

SWITCH
6
454
127
487
verbose?
verbose?
1
1
-1000

SWITCH
7
556
117
589
debug?
debug?
0
1
-1000

TEXTBOX
6
603
156
648
debug is voor interne algorthme checks. Normaal off
12
0.0
1

TEXTBOX
7
494
157
524
Vertel wat je aan het doen bent. Normaal off
12
0.0
1

BUTTON
1574
541
1772
574
Force directed netwerk
graphView
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1569
20
1665
53
Map view
mapView
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1569
69
1689
102
labels on/off
toggleLabels
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

CHOOSER
11
134
160
179
inputFileDelimiter
inputFileDelimiter
"," ";"
0

BUTTON
1574
581
1711
614
Cirkel netwerk
clear-patches\nlayout-circle turtles 310
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1717
582
1853
615
"Tutte" netwerk
clear-patches\nlayout-tutte (conversionAssets with [link-neighbors = 1 ]) connectionLinks 310
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1575
618
1822
651
Netwerk vanuit ElectricitygridTenneT
centerNetworkOnElectricityGrid
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1573
426
1685
459
NIL
selectAsset
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

MONITOR
1691
419
1841
464
Naam selected
[humanReadableName] of selectedAsset
17
1
11

BUTTON
1573
501
1834
534
NIL
centerNetworkOnSelectedAsset
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
1574
465
1713
498
unselect Asset
reset-perspective
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

TEXTBOX
23
204
151
309
Electricity - White\nH2 - Blue\nNatgas - Yellow\nCoal - Brown\nSteam - Green\nLTheat - Orange\nHTheat - Red\n
12
0.0
1

BUTTON
11
69
75
103
NIL
go
NIL
1
T
OBSERVER
NIL
G
NIL
NIL
1

BUTTON
97
26
163
60
NIL
startNewRun
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

CHOOSER
14
325
193
370
decisionMakingModel
decisionMakingModel
"Reactive" "Current" "Proactive" "Collaborative"
2

MONITOR
1462
19
1551
92
Year is
year
0
1
18

SWITCH
6
409
169
442
provideWarnings?
provideWarnings?
0
1
-1000

BUTTON
1588
142
1702
175
Save image
export-view (word \"windmaster-view\" \ndate-and-time \".png\")
NIL
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

BUTTON
79
75
213
108
run simulation
go
T
1
T
OBSERVER
NIL
NIL
NIL
NIL
1

@#$#@#$#@
# Windmaster

This is the proof of concept simulation developed as a part of the Windmaster project, that aims to develop a proof of concept adaptive energy infrastructure investment plan for the Rotterdam Port area.

## High level model narrative

In the port region a large number of technical investments must take place if we are to reduce out CO2 footprint. These investment will radically alter the energy landscape of the port, requiring more and different energy infrastructure. Current network planning and investment models of infrastructure providers are mainly reactive, due to institutional constraints and tradition of very high operational reliability. The model explores the impact of alternative decision making policies by infrastructure provides, that are much more proactive and collaborative than now. Model consists of a decision making submodel and a technical submodel.




## Assumptions about the technical submodel
### General Assumptions 

  1. All data provided with this model are based on public information.
  1. There are 5 types of energy carriers considered in the model : Coal,Natgas, Refgas,Petcokes,Resfuel,Oilrest,Waste,Electricity,Steam:Htheat:Ltheat:H2
  1. Every entity is either a conversion asset (node) or a line connecting them (link)
  1. All flows and conversions are expressed in their  energy content in MW
  1. Conversion assets that have no outputs are considered final demands
  1. Conversion Assets are defined by a specific type of energy carrier and their energy content in MW
  1. Outputs are defined in terms of conversion eficiencies of an input flow into one of the 5 energy carriers
  1. The energy is not balanced across an conversion assets, as efficiency is always lower then 1
  1. A infrastructure node, such as a substation,  has a specific input and it outputs the same energy carrier with efficiency of 1
  1. Over the entire technical model the energy is balanced, including imports from  Markets and inefficiencies lost to the Environment
  1. ...

### Stedin network
  1. The local ring network that clients connect to is represented by the sum of individual lines from a substation to clients.
  1. ...

### Tennet network
  1. Grid security is expressed by computed MW line load, vs maximum designed line capacity.
  1. There is no difference between line capacity and substation capacity
  1. The TenneT grid load flow is performed using matpower, using real TenneT data, based on  phd thesis of Dr. ir. M. Van Blijswijk
  1. The Agent Based model uses a simplified representation of the TenneT grid, that aggregates data from the detailed model 
### Gasunie network

### HBR network
  1. ...

### PZH network
  1. Does not manage any physical network in the model


## Assumptions about the behavioural submodel
### General Assumptions 
  1. Markets exist per energy carrier, and are conversion assets that have no energy input and no energy output defined, but do have streams from and to to particular other conversion assets. This represents  that buying and selling to the market, via a connection link of unlimited capacity, defined by UNDEF.

### Stedin 

### Tennet 

### Gasunie 

### HBR 

### PZH 


## Technical implementation details
Model uses the default CSV extension for loading configuration files and the [NetLogo-py](https://github.com/NetLogo/Python-Extension) extension for communicating with python. 
Experiments are performed using [EMA Workbench](https://github.com/quaquel/EMAworkbench)

## CREDITS AND REFERENCES
Created by Dr. ir. Igor Nikolic and ir. Ton Wurth in 2019
This document is copy of the README.md in the model directory. The [README](README.md) file is leading.
@#$#@#$#@
default
true
0
Polygon -7500403 true true 150 5 40 250 150 205 260 250

airplane
true
0
Polygon -7500403 true true 150 0 135 15 120 60 120 105 15 165 15 195 120 180 135 240 105 270 120 285 150 270 180 285 210 270 165 240 180 180 285 195 285 165 180 105 180 60 165 15

arrow
true
0
Polygon -7500403 true true 150 0 0 150 105 150 105 293 195 293 195 150 300 150

box
false
0
Polygon -7500403 true true 150 285 285 225 285 75 150 135
Polygon -7500403 true true 150 135 15 75 150 15 285 75
Polygon -7500403 true true 15 75 15 225 150 285 150 135
Line -16777216 false 150 285 150 135
Line -16777216 false 150 135 15 75
Line -16777216 false 150 135 285 75

bug
true
0
Circle -7500403 true true 96 182 108
Circle -7500403 true true 110 127 80
Circle -7500403 true true 110 75 80
Line -7500403 true 150 100 80 30
Line -7500403 true 150 100 220 30

building institution
false
0
Rectangle -7500403 true true 0 60 300 270
Rectangle -16777216 true false 130 196 168 256
Rectangle -16777216 false false 0 255 300 270
Polygon -7500403 true true 0 60 150 15 300 60
Polygon -16777216 false false 0 60 150 15 300 60
Circle -1 true false 135 26 30
Circle -16777216 false false 135 25 30
Rectangle -16777216 false false 0 60 300 75
Rectangle -16777216 false false 218 75 255 90
Rectangle -16777216 false false 218 240 255 255
Rectangle -16777216 false false 224 90 249 240
Rectangle -16777216 false false 45 75 82 90
Rectangle -16777216 false false 45 240 82 255
Rectangle -16777216 false false 51 90 76 240
Rectangle -16777216 false false 90 240 127 255
Rectangle -16777216 false false 90 75 127 90
Rectangle -16777216 false false 96 90 121 240
Rectangle -16777216 false false 179 90 204 240
Rectangle -16777216 false false 173 75 210 90
Rectangle -16777216 false false 173 240 210 255
Rectangle -16777216 false false 269 90 294 240
Rectangle -16777216 false false 263 75 300 90
Rectangle -16777216 false false 263 240 300 255
Rectangle -16777216 false false 0 240 37 255
Rectangle -16777216 false false 6 90 31 240
Rectangle -16777216 false false 0 75 37 90
Line -16777216 false 112 260 184 260
Line -16777216 false 105 265 196 265

butterfly
true
0
Polygon -7500403 true true 150 165 209 199 225 225 225 255 195 270 165 255 150 240
Polygon -7500403 true true 150 165 89 198 75 225 75 255 105 270 135 255 150 240
Polygon -7500403 true true 139 148 100 105 55 90 25 90 10 105 10 135 25 180 40 195 85 194 139 163
Polygon -7500403 true true 162 150 200 105 245 90 275 90 290 105 290 135 275 180 260 195 215 195 162 165
Polygon -16777216 true false 150 255 135 225 120 150 135 120 150 105 165 120 180 150 165 225
Circle -16777216 true false 135 90 30
Line -16777216 false 150 105 195 60
Line -16777216 false 150 105 105 60

car
false
0
Polygon -7500403 true true 300 180 279 164 261 144 240 135 226 132 213 106 203 84 185 63 159 50 135 50 75 60 0 150 0 165 0 225 300 225 300 180
Circle -16777216 true false 180 180 90
Circle -16777216 true false 30 180 90
Polygon -16777216 true false 162 80 132 78 134 135 209 135 194 105 189 96 180 89
Circle -7500403 true true 47 195 58
Circle -7500403 true true 195 195 58

circle
false
0
Circle -7500403 true true 0 0 300

circle 2
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240

cow
false
0
Polygon -7500403 true true 200 193 197 249 179 249 177 196 166 187 140 189 93 191 78 179 72 211 49 209 48 181 37 149 25 120 25 89 45 72 103 84 179 75 198 76 252 64 272 81 293 103 285 121 255 121 242 118 224 167
Polygon -7500403 true true 73 210 86 251 62 249 48 208
Polygon -7500403 true true 25 114 16 195 9 204 23 213 25 200 39 123

cylinder
false
0
Circle -7500403 true true 0 0 300

dot
false
0
Circle -7500403 true true 90 90 120

face happy
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 255 90 239 62 213 47 191 67 179 90 203 109 218 150 225 192 218 210 203 227 181 251 194 236 217 212 240

face neutral
false
0
Circle -7500403 true true 8 7 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Rectangle -16777216 true false 60 195 240 225

face sad
false
0
Circle -7500403 true true 8 8 285
Circle -16777216 true false 60 75 60
Circle -16777216 true false 180 75 60
Polygon -16777216 true false 150 168 90 184 62 210 47 232 67 244 90 220 109 205 150 198 192 205 210 220 227 242 251 229 236 206 212 183

factory
false
0
Rectangle -7500403 true true 76 194 285 270
Rectangle -7500403 true true 36 95 59 231
Rectangle -16777216 true false 90 210 270 240
Line -7500403 true 90 195 90 255
Line -7500403 true 120 195 120 255
Line -7500403 true 150 195 150 240
Line -7500403 true 180 195 180 255
Line -7500403 true 210 210 210 240
Line -7500403 true 240 210 240 240
Line -7500403 true 90 225 270 225
Circle -1 true false 37 73 32
Circle -1 true false 55 38 54
Circle -1 true false 96 21 42
Circle -1 true false 105 40 32
Circle -1 true false 129 19 42
Rectangle -7500403 true true 14 228 78 270

fish
false
0
Polygon -1 true false 44 131 21 87 15 86 0 120 15 150 0 180 13 214 20 212 45 166
Polygon -1 true false 135 195 119 235 95 218 76 210 46 204 60 165
Polygon -1 true false 75 45 83 77 71 103 86 114 166 78 135 60
Polygon -7500403 true true 30 136 151 77 226 81 280 119 292 146 292 160 287 170 270 195 195 210 151 212 30 166
Circle -16777216 true false 215 106 30

flag
false
0
Rectangle -7500403 true true 60 15 75 300
Polygon -7500403 true true 90 150 270 90 90 30
Line -7500403 true 75 135 90 135
Line -7500403 true 75 45 90 45

flower
false
0
Polygon -10899396 true false 135 120 165 165 180 210 180 240 150 300 165 300 195 240 195 195 165 135
Circle -7500403 true true 85 132 38
Circle -7500403 true true 130 147 38
Circle -7500403 true true 192 85 38
Circle -7500403 true true 85 40 38
Circle -7500403 true true 177 40 38
Circle -7500403 true true 177 132 38
Circle -7500403 true true 70 85 38
Circle -7500403 true true 130 25 38
Circle -7500403 true true 96 51 108
Circle -16777216 true false 113 68 74
Polygon -10899396 true false 189 233 219 188 249 173 279 188 234 218
Polygon -10899396 true false 180 255 150 210 105 210 75 240 135 240

house
false
0
Rectangle -7500403 true true 45 120 255 285
Rectangle -16777216 true false 120 210 180 285
Polygon -7500403 true true 15 120 150 15 285 120
Line -16777216 false 30 120 270 120

leaf
false
0
Polygon -7500403 true true 150 210 135 195 120 210 60 210 30 195 60 180 60 165 15 135 30 120 15 105 40 104 45 90 60 90 90 105 105 120 120 120 105 60 120 60 135 30 150 15 165 30 180 60 195 60 180 120 195 120 210 105 240 90 255 90 263 104 285 105 270 120 285 135 240 165 240 180 270 195 240 210 180 210 165 195
Polygon -7500403 true true 135 195 135 240 120 255 105 255 105 285 135 285 165 240 165 195

line
true
0
Line -7500403 true 150 0 150 300

line half
true
0
Line -7500403 true 150 0 150 150

pentagon
false
0
Polygon -7500403 true true 150 15 15 120 60 285 240 285 285 120

person
false
0
Circle -7500403 true true 110 5 80
Polygon -7500403 true true 105 90 120 195 90 285 105 300 135 300 150 225 165 300 195 300 210 285 180 195 195 90
Rectangle -7500403 true true 127 79 172 94
Polygon -7500403 true true 195 90 240 150 225 180 165 105
Polygon -7500403 true true 105 90 60 150 75 180 135 105

plant
false
0
Rectangle -7500403 true true 135 90 165 300
Polygon -7500403 true true 135 255 90 210 45 195 75 255 135 285
Polygon -7500403 true true 165 255 210 210 255 195 225 255 165 285
Polygon -7500403 true true 135 180 90 135 45 120 75 180 135 210
Polygon -7500403 true true 165 180 165 210 225 180 255 120 210 135
Polygon -7500403 true true 135 105 90 60 45 45 75 105 135 135
Polygon -7500403 true true 165 105 165 135 225 105 255 45 210 60
Polygon -7500403 true true 135 90 120 45 150 15 180 45 165 90

sheep
false
15
Circle -1 true true 203 65 88
Circle -1 true true 70 65 162
Circle -1 true true 150 105 120
Polygon -7500403 true false 218 120 240 165 255 165 278 120
Circle -7500403 true false 214 72 67
Rectangle -1 true true 164 223 179 298
Polygon -1 true true 45 285 30 285 30 240 15 195 45 210
Circle -1 true true 3 83 150
Rectangle -1 true true 65 221 80 296
Polygon -1 true true 195 285 210 285 210 240 240 210 195 210
Polygon -7500403 true false 276 85 285 105 302 99 294 83
Polygon -7500403 true false 219 85 210 105 193 99 201 83

square
false
0
Rectangle -7500403 true true 30 30 270 270

square 2
false
0
Rectangle -7500403 true true 30 30 270 270
Rectangle -16777216 true false 60 60 240 240

star
false
0
Polygon -7500403 true true 151 1 185 108 298 108 207 175 242 282 151 216 59 282 94 175 3 108 116 108

target
false
0
Circle -7500403 true true 0 0 300
Circle -16777216 true false 30 30 240
Circle -7500403 true true 60 60 180
Circle -16777216 true false 90 90 120
Circle -7500403 true true 120 120 60

tree
false
0
Circle -7500403 true true 118 3 94
Rectangle -6459832 true false 120 195 180 300
Circle -7500403 true true 65 21 108
Circle -7500403 true true 116 41 127
Circle -7500403 true true 45 90 120
Circle -7500403 true true 104 74 152

triangle
false
0
Polygon -7500403 true true 150 30 15 255 285 255

triangle 2
false
0
Polygon -7500403 true true 150 30 15 255 285 255
Polygon -16777216 true false 151 99 225 223 75 224

truck
false
0
Rectangle -7500403 true true 4 45 195 187
Polygon -7500403 true true 296 193 296 150 259 134 244 104 208 104 207 194
Rectangle -1 true false 195 60 195 105
Polygon -16777216 true false 238 112 252 141 219 141 218 112
Circle -16777216 true false 234 174 42
Rectangle -7500403 true true 181 185 214 194
Circle -16777216 true false 144 174 42
Circle -16777216 true false 24 174 42
Circle -7500403 false true 24 174 42
Circle -7500403 false true 144 174 42
Circle -7500403 false true 234 174 42

turtle
true
0
Polygon -10899396 true false 215 204 240 233 246 254 228 266 215 252 193 210
Polygon -10899396 true false 195 90 225 75 245 75 260 89 269 108 261 124 240 105 225 105 210 105
Polygon -10899396 true false 105 90 75 75 55 75 40 89 31 108 39 124 60 105 75 105 90 105
Polygon -10899396 true false 132 85 134 64 107 51 108 17 150 2 192 18 192 52 169 65 172 87
Polygon -10899396 true false 85 204 60 233 54 254 72 266 85 252 107 210
Polygon -7500403 true true 119 75 179 75 209 101 224 135 220 225 175 261 128 261 81 224 74 135 88 99

wheel
false
0
Circle -7500403 true true 3 3 294
Circle -16777216 true false 30 30 240
Line -7500403 true 150 285 150 15
Line -7500403 true 15 150 285 150
Circle -7500403 true true 120 120 60
Line -7500403 true 216 40 79 269
Line -7500403 true 40 84 269 221
Line -7500403 true 40 216 269 79
Line -7500403 true 84 40 221 269

wolf
false
0
Polygon -16777216 true false 253 133 245 131 245 133
Polygon -7500403 true true 2 194 13 197 30 191 38 193 38 205 20 226 20 257 27 265 38 266 40 260 31 253 31 230 60 206 68 198 75 209 66 228 65 243 82 261 84 268 100 267 103 261 77 239 79 231 100 207 98 196 119 201 143 202 160 195 166 210 172 213 173 238 167 251 160 248 154 265 169 264 178 247 186 240 198 260 200 271 217 271 219 262 207 258 195 230 192 198 210 184 227 164 242 144 259 145 284 151 277 141 293 140 299 134 297 127 273 119 270 105
Polygon -7500403 true true -1 195 14 180 36 166 40 153 53 140 82 131 134 133 159 126 188 115 227 108 236 102 238 98 268 86 269 92 281 87 269 103 269 113

x
false
0
Polygon -7500403 true true 270 75 225 30 30 225 75 270
Polygon -7500403 true true 30 75 75 30 270 225 225 270
@#$#@#$#@
NetLogo 6.0.4
@#$#@#$#@
@#$#@#$#@
@#$#@#$#@
<experiments>
  <experiment name="test" repetitions="100" runMetricsEveryStep="false">
    <setup>setup</setup>
    <go>go</go>
    <timeLimit steps="30"/>
    <metric>reportScenario</metric>
    <metric>reportRealisedScenarioEvents</metric>
    <enumeratedValueSet variable="provideWarnings?">
      <value value="true"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="inputFileDelimiter">
      <value value="&quot;,&quot;"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="debug?">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="verbose?">
      <value value="false"/>
    </enumeratedValueSet>
    <enumeratedValueSet variable="decisionMakingModel">
      <value value="&quot;Current&quot;"/>
    </enumeratedValueSet>
  </experiment>
</experiments>
@#$#@#$#@
@#$#@#$#@
default
0.0
-0.2 0 0.0 1.0
0.0 1 1.0 0.0
0.2 0 0.0 1.0
link direction
true
0
Line -7500403 true 150 150 90 180
Line -7500403 true 150 150 210 180
@#$#@#$#@
0
@#$#@#$#@
