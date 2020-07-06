import random
import networkx as nx
import pandas as pd
import numpy as np
import math
import warnings
from networkx.exception import NetworkXError

from profile import profile  # @UnresolvedImport
from collections import defaultdict

# TODO:: make all code pep8 compliant

warnings.filterwarnings("ignore")

conversionAssets_file = 'data/conversionAssets.csv'
connectionLinks_file = 'data/connectionLinks.csv'
investID_file = 'data/investIDwindmaster.csv'
all_assets = pd.read_csv(conversionAssets_file, sep=',', header=17).fillna('0')
connectionLinks_elec = pd.read_csv(
    connectionLinks_file, header=16).fillna(100000)
logical = (connectionLinks_elec.loc[:, 'Status'] == 'Existing') &\
          (connectionLinks_elec.loc[:, 'Feedstock carried'] == 'Electricity')
connectionLinks_elec = connectionLinks_elec[logical]
investment_id = pd.read_csv(investID_file, delimiter=None, header=0)
lost_stedin_customers = []

electricity_grid = nx.from_pandas_edgelist(
                                connectionLinks_elec,
                                source=connectionLinks_elec.columns.values[1],
                                target=connectionLinks_elec.columns.values[2],
                                edge_attr=True,)

# Shortkeys for relevant edge attributes
linkCapacity = nx.get_edge_attributes(
    electricity_grid, connectionLinks_elec.columns.values[4])
linkOwner = nx.get_edge_attributes(
    electricity_grid, connectionLinks_elec.columns.values[5])
linkID = nx.get_edge_attributes(electricity_grid,
                                connectionLinks_elec.columns.values[0])
linkLength = nx.get_edge_attributes(
    electricity_grid, connectionLinks_elec.columns.values[8])

# List of events thast agents expect will happen, used for commnication fom NetLogo to technical model
demandExpectations = []
# 0,1,2,3 [ "Reactive" , "Current" , "Proactive" , "Collaborative" ], used globally
decisionMakingModel = 0
# the current event happening, used for communication between NetLogo en tehcnical model
event = []

assetTypes_file = 'data/assetTypes.csv'
assetTypes = pd.read_csv(assetTypes_file, header=None)
assetTypeTechnologies_file = "data/assetTypeTechnologies.csv"
assetTypeTechnologies = pd.read_csv(assetTypeTechnologies_file, header=None)

# Shortkeys for relevant conversion assets
boiler = all_assets.loc[:, 'assetTypes'] == 'Boiler'
cogen = all_assets.loc[:, 'assetTypes'] == 'Cogen'
furnace = all_assets.loc[:, 'assetTypes'] == 'Furnace'
electrolyzer = all_assets.loc[:, 'assetTypes'] == 'Electrolyzer_H2O'
smr = all_assets.loc[:, 'assetTypes'] == 'SMR'
smr_ccs = all_assets.loc[:, 'assetTypes'] == 'SMR_CCS'
incinerator = all_assets.loc[:, 'assetTypes'] == 'Incinerator'
gasifier = all_assets.loc[:, 'assetTypes'] == 'Gasifier'
electrolyzer_brine = all_assets.loc[:, 'assetTypes'] == 'Electrolyzer_Brine'
electrolyzer_MV = all_assets.loc[:, 'assetTypes'] == 'C76'
electrolyzer_Simon = all_assets.loc[:, 'assetTypes'] == 'C79'
syntheticfuel_MV = all_assets.loc[:, 'assetTypes'] == 'D34'
syntheticfuel_Simon = all_assets.loc[:, 'assetTypes'] == 'D35'

powergen_baseload_ind = all_assets.loc[:, 'assetTypes'] == 'Powergen_baseloadindust'
powergen_baseload = all_assets.loc[:, 'assetTypes'] == 'Powergen_baseload'
powergen_flexible = all_assets.loc[:, 'assetTypes'] == 'Powergen_flexible'

# TODO:: give meaningfull description
InvestSetsDF = pd.read_csv('data/InvestmentSets.csv', sep=';')
InvestID = pd.read_csv('data/investIDwindmaster.csv')

# :TODO  We might need to update these after removal !!
# Shortkeys for relevant demands
core_sites = []
for i in range(0, 43):
    site_id = 'D'+str(i+1)
    if site_id != 'D34' and site_id != 'D35':
        core_sites.append(site_id)
core_sites.append('D47')

all_power_demand = all_assets.iloc[:, 2].isin(core_sites)

# Shortkeys for relevant supply 
# column 2 is 'Conversion asset ID [string] – Must be unique'
off_shore_MV = all_assets.iloc[:, 2] == 'S2'
off_shore_Simons = all_assets.iloc[:, 2] == 'S3'
britned = all_assets.iloc[:, 2] == 'S4'
restofNL = all_assets.iloc[:, 2] == 'S5'

stations = all_assets[all_assets.iloc[:, 2].str.contains('Stedin') |
                      all_assets.iloc[:, 2].str.contains('TenneT')]

stations = stations[stations.iloc[:, 14] == 'Electricity']
conversionAssets_elec = all_assets[boiler | cogen | furnace | electrolyzer |
                                   smr | smr_ccs | incinerator | gasifier
                                   ].reset_index(drop=True)

conversionAssets_elec = conversionAssets_elec[conversionAssets_elec.iloc[:, 3] == 'existing']

site_demands = all_assets[all_power_demand |
                         electrolyzer_brine].reset_index(drop=True)
# energySupply = all_assets[off_shore_MV | off_shore_Simons |
#                           britned | restofNL].reset_index(drop=True)


energySupply = all_assets[off_shore_MV | off_shore_Simons |
                        britned | restofNL | powergen_baseload_ind|
                        powergen_flexible| powergen_baseload].reset_index(drop=True)

# TODO:: this seems strange, we only keep power demand
# what about gas demands?
for i, row in site_demands.iloc[:, 14:16].iterrows():
    row = row.values
    row = [entry.split(':') for entry in row]
    row = list(zip(*row))
    e_demand = 0
    for entry in row:
        feedstock, demand = entry
        if feedstock == 'Electricity':
            e_demand = demand
            break
    
    site_demands.iloc[i, 15] = e_demand

stedin_stations = ['StedinMV', 'StedinEur', 'BotA_MerseyHuntsman',
                   'StedinTheems', 'StedinGerbrand', 'StedinBotl', 'StedinVondel']
tennet150_stations = ['TenneT150MV_trans', 'TenneT150MV_gen',
                      'TenneT150Eur_trans', 'TenneT150Eur_cust',
                      'TenneT150Mersey_trans', 'TenneT150Mersey_gen',
                      'TenneT150Botl_trans', 'TenneT150Botl_gen', 'TenneT150Botl_cust',
                      'TenneT150Theems_trans', 'TenneT150Theems_gen',
                      'TenneT150Gerbrand_trans', 'TenneT150Gerbrand_gen',
                      'TenneT150Vondel_gen', 'TenneT150Vondel_trans',
                      'TenneT150Geervl_gen',
                      'TenneT150Waalh_gen',
                      ]
tennet380_stations = ['TenneT380MV_gen', 'TenneT380MV_line', 'TenneT380MV_trans',
                      'TenneT380Simonsh_gen', 'TenneT380Simonsh_trans', 'TenneT380Simonsh_line',
                      'TenneT380Krimpen_line', 'TenneT380Krimpen_trans',
                      'TenneT380restNL_line',
                      'TenneT380Bleiswijk_line']
# tennet150_stations.append('TenneT380restNL_line')
sink_stations = tennet150_stations + ['TenneT380restNL_line', ]

staged_investments = defaultdict(list)
# ## INIT GASMODEL ##

# initialize capacity dataframe and assetdictionary
startyear = 2020
endyear = 2055  # !! important to define !!
year = startyear
GTSgrid3switch = False



def initdf_cap():
    dfCap = pd.DataFrame(np.array([[0]*37]*10),
                         columns=list(range(2018, endyear, 1)))
    dfCap['size 1 link'] = [20000, 20000, 20000,
                            20000, 20000, 4000, 4000, 4000, 20000, 40000]
    dfCap['investID'] = ['NewH2grid1a', 'NewH2grid1b', 'NewH2grid1c',
                         'NewH2grid1d', 'GTSgrid1H2', 'GTSgrid2H2',
                         'GTSgrid3H2', 'GTSgrid3proactH2', 'NewH2grid2',
                         'NewH2grid3']
    return dfCap


def init_asset_dict(initialAssets):
    # TODO:: very dirty hack to fix indexing problems
    initialAssets = initialAssets.copy().iloc[:, :-2]

    H2supplyMV1 = initialAssets.iloc[:, 2] == 'C75'
    H2supplyMV2 = initialAssets.iloc[:, 2] == 'C76'
    H2supplyMV3 = initialAssets.iloc[:, 2] == 'C77'
    assetsH2supplyMV = initialAssets[H2supplyMV1 | H2supplyMV2 | H2supplyMV3]

    H2supplyBotlek1 = initialAssets.iloc[:, 2] == 'C78'
    H2supplyBotlek2 = initialAssets.iloc[:, 2] == 'C79'
    assetsH2supplyBotlek = initialAssets[H2supplyBotlek1 | H2supplyBotlek2]

    H2demandb1 = initialAssets.iloc[:, 2] == 'D34'
    H2demandb2 = initialAssets.iloc[:, 28] == 'ChangecurrentH2demandb'
    assetsH2demandb = initialAssets[H2demandb1 | H2demandb2]

    H2demandc2 = initialAssets.iloc[:, 2] == 'D35'
    H2demandc1 = initialAssets.iloc[:, 28] == 'ChangecurrentH2demandc'
    assetsH2demandc = initialAssets[H2demandc1 | H2demandc2]

    H2demandd1 = initialAssets.iloc[:, 28] == 'ChangecurrentH2demandd'
    assetsH2demandd = initialAssets[H2demandd1]

    H2demande1 = initialAssets.iloc[:, 2] == 'D36'
    assetsH2demande = initialAssets[H2demande1]

    Gasdemand1 = initialAssets.iloc[:, 2] == 'C31'
    Gasdemand2 = initialAssets.iloc[:, 2] == 'C32'
    Gasdemand3 = initialAssets.iloc[:, 2] == 'C48'
    Gasdemand4 = initialAssets.iloc[:, 2] == 'C62'
    Gasdemand5 = initialAssets.iloc[:, 2] == 'C78'
    Gasdemand6 = initialAssets.iloc[:, 2] == 'D37'

    assetsDict = {}

    for i in range(2018, endyear, 1):
        assetsDict[i] = initialAssets[H2supplyMV1 | H2supplyMV2 | H2supplyMV3 | H2supplyBotlek1 | H2supplyBotlek2 | H2demandb1 | H2demandb2 |
                                      H2demandc1 | H2demandc2 | H2demandd1 | H2demande1 | Gasdemand1 | Gasdemand2 | Gasdemand3 | Gasdemand4 | Gasdemand5 | Gasdemand6]
        H2d = [0]*79
        Ngasd = [0, 9, 85, 128, 128, 0, 150, 0, 0, 87, 0, 93, 1475, 91, 70, 23, 0, 24, 0, 0, 28, 0, 0, 150, 9, 31, 31, 36, 6, 156, 286, 471, 520, 5, 12, 5, 312,
                 181, 56, 0, 0, 30, 33, 72, 83, 68, 448, 0, 0, 0, 4, 30, 0, 1, 2, 7, 21, 751, 778, 296, 0, 0, 34, 0, 0, 25, 0, 0, 180, 0, 0, 400, 0, 400, 0, 0, 0, 0, 422]
        petcoke = [0]*8+[162]+[0]+[0]+[93]+7*[0]+[26]+[0]+[0]+[30] + \
            38*[0]+[200]+[0]+[0]+[37]+[0]+[0]+[26]+[0]+[0]+[194]+[0]*8
        refgas = [0]*7+[566]+[0]*2+[327]+[0]*7+[90]+[0]*2+[105]+[0]*15+[0]+[0]+[0]*8+[231] + \
            [838]+[192]+[0]+[0]+[0]+[0]*7+[699]+[0] + \
            [0]+[129]+[0]+[0]+[92]+[0]+[0]+[680]+[0]*9
        restfuel = 39*[0]+[24]+[65]+11*[0]+[10]+26*[0]
        assetsDict[i]["H2demand"] = H2d
        assetsDict[i]['NGasdemand'] = Ngasd
        assetsDict[i]["PetCokedemand"] = petcoke
        assetsDict[i]['RefGasdemand'] = refgas
        assetsDict[i]['Restfuel'] = restfuel
    return assetsDict


assetsDict = init_asset_dict(all_assets)
dfCap = initdf_cap()


def get_needed_gas_investments(demandExpectations):
    keep = change_gas_asset_demand(demandExpectations, False)
    return keep


def change_gas_asset_demand(EventList, add):
    df = assetsDict[year].copy()
    relevant_assets = set(assetsDict[year].iloc[:, 2])

    for event in EventList:
        assetid = event[0]
        assetType = event[1]

        if assetid in relevant_assets:
            df = df.reset_index(drop=True)
            bool = df.iloc[:, 2] == assetid  # @ReservedAssignment
            if event[1] == -1 and event[2] == -1:
                remove_gas_asset(assetid)
            if event[4] == -1:
                if assetTypes.iloc[assetType, 0] == 'Boiler' or\
                   assetTypes.iloc[assetType, 0] == 'Furnace' or\
                   assetTypes.iloc[assetType, 0] == 'Cogen' or\
                   assetTypes.iloc[assetType, 0] == 'Powergen_flexible':
                    if assetTypeTechnologies[event[2]][event[1]] == 'HybridH2':
                        index = df[bool].index.values.astype(int)[0]
                        df.iloc[index, 36] = max(
                            df.iloc[index, 37], df.iloc[index, 38], df.iloc[index, 39], df.iloc[index, 40])
                    if assetTypeTechnologies[event[2]][event[1]] == 'H2':
                        index = df[bool].index.values.astype(int)[0]
                        df.iloc[index, 36] = max(df.iloc[index, 37:41])
                        df.iloc[index, 37:41] = 0
            if event[4] >= 0:
                if assetid in {'D2', 'D34', 'D4', 'D7', 'D36'}:
                    index = df[bool].index.values.astype(int)[0]
                    df.iloc[index, 36] += event[4]
            if assetid == 'C66':
                df = df.reset_index(drop=True)
                bool = df.iloc[:, 2] == assetid  # @ReservedAssignment
                index = df[bool].index.values.astype(int)[0]
                df.iloc[index, 37] = 0
            if assetid == 'D34' or assetid == 'D35':
                index = df[bool].index.values.astype(int)[0]
                df.iloc[index, 36] += 4300
            if assetid == 'C76' or assetid == 'C79':
                index = df[bool].index.values.astype(int)[0]
                df.iloc[index, 36] += 750
            if assetid == "C75" or assetid == "C78":
                index = df[bool].index.values.astype(int)[0]
                df.iloc[index, 36] += 300
                df.iloc[index, 37] += 400

    if add:
        if len(check_gas_investment_needed(df)) == 0:
            # TODO:: move out of this and to seperate change function
            assetsDict[year] = df
            return True, df
        else:
            return False
    else:
        keep = check_gas_investment_needed(df)
        return keep


def check_gas_investment_needed(dataframe):
    # this function is used within the change_gas_asset_demand function
    df = dataframe

    # determine demands
    H2demandb1 = df.iloc[:, 2] == 'D34'
    H2demandb2 = df.iloc[:, 28] == 'ChangecurrentH2demandb'
    assetsH2demandb = df[H2demandb1 | H2demandb2]
    H2demandc1 = df.iloc[:, 28] == 'ChangecurrentH2demandc'
    H2demandc2 = df.iloc[:, 2] == 'D35'
    assetsH2demandc = df[H2demandc1 | H2demandc2]
    H2demandd1 = df.iloc[:, 28] == 'ChangecurrentH2demandd'
    assetsH2demandd = df[H2demandd1]
    H2demande1 = df.iloc[:, 2] == 'D36'
    assetsH2demande = df[H2demande1]

    amountH2demandB = assetsH2demandb["H2demand"].sum()
    amountH2demandC = assetsH2demandc["H2demand"].sum()
    amountH2demandD = assetsH2demandd["H2demand"].sum()
    amountH2demandE = assetsH2demande["H2demand"].sum()

    # determine supply and import and export
    H2supplyMV1 = df.iloc[:, 2] == 'C75'
    H2supplyMV2 = df.iloc[:, 2] == 'C76'
    importexport = df.iloc[:, 2] == 'C77'
    assetsH2supplyMV = df[H2supplyMV1 | H2supplyMV2]
    assetsH2importexport = df[importexport]

    H2supplyBotlek1 = df.iloc[:, 2] == 'C78'
    H2supplyBotlek2 = df.iloc[:, 2] == 'C79'
    assetsH2supplyBotlek = df[H2supplyBotlek1 | H2supplyBotlek2]

    amountH2supplyMV = assetsH2supplyMV["H2demand"].sum()
    amountH2supplyBotlek = assetsH2supplyBotlek["H2demand"].sum()
    amountH2ImportExport = (amountH2supplyMV + amountH2supplyBotlek) - (
        amountH2demandB + amountH2demandC + amountH2demandD + amountH2demandE)
    amountH2supplyMV = amountH2supplyMV + abs(amountH2ImportExport)

    # determine gas demands
    boolGasDemand1A = df.iloc[:, 29] == "GTS1b"
    boolGasDemand1B = df.iloc[:, 29] == "GTS1c"
    boolGasDemand1C = df.iloc[:, 29] == "GTS1d"
    boolGasDemand2B = df.iloc[:, 29] == "GTS2c"
    boolGasDemand2C = df.iloc[:, 29] == "GTS2d"
    boolGasDemand3C = df.iloc[:, 29] == "GTS3d"

    assetsGasDemand1A = df[boolGasDemand1A]
    assetsGasDemand1B = df[boolGasDemand1B]
    assetsGasDemand1C = df[boolGasDemand1C]
    assetsGasDemand2B = df[boolGasDemand2B]
    assetsGasDemand2C = df[boolGasDemand2C]
    assetsGasDemand3C = df[boolGasDemand3C]

    amountGasDemand1A = assetsGasDemand1A["NGasdemand"].sum()
    amountGasDemand1B = amountGasDemand1A + \
        assetsGasDemand1B["NGasdemand"].sum()
    amountGasDemand1C = amountGasDemand1B + \
        assetsGasDemand1C["NGasdemand"].sum()
    amountGasDemand2B = assetsGasDemand2B["NGasdemand"].sum()
    amountGasDemand2C = amountGasDemand2B + \
        assetsGasDemand2C["NGasdemand"].sum()
    amountGasDemand3C = assetsGasDemand3C["NGasdemand"].sum()
    amountGasDemand1D = amountGasDemand1C + amountGasDemand2C + amountGasDemand3C

    if GTSgrid3switch == True:
        amountGasDemand2C = amountGasDemand2C + amountGasDemand3C
        amountGasDemand3C = 0

    # determine capacity needs
    H2transportneedA = amountH2supplyMV
    H2transportneedB = 0
    if amountH2demandB < amountH2supplyMV and\
       amountH2supplyBotlek < (amountH2demandC + amountH2demandD + amountH2demandE):
        H2transportneedB = amountH2supplyMV - amountH2demandB
    if amountH2demandB > amountH2supplyMV and\
       amountH2supplyBotlek > (amountH2demandC + amountH2demandD + amountH2demandE):
        H2transportneedB = amountH2supplyBotlek - \
            (amountH2demandC + amountH2demandD + amountH2demandE)
    H2transportneedC = amountH2demandD + amountH2demandE
    H2transportneedD = amountH2demandE

    # get installed capacity out of dataframe for the year that is requested
    installedH2transportcapacityA = dfCap[year][0] + \
        dfCap[year][4] + dfCap[year][8] + dfCap[year][9]
    installedH2transportcapacityB = dfCap[year][1] + \
        dfCap[year][5] + dfCap[year][4] + dfCap[year][8] + dfCap[year][9]
    installedH2transportcapacityC = dfCap[year][2] + dfCap[year][6] + \
        dfCap[year][7] + dfCap[year][4] + dfCap[year][8] + dfCap[year][9]
    installedH2transportcapacityD = dfCap[year][3] + \
        dfCap[year][4] + dfCap[year][8] + dfCap[year][9]

    # check if there are bottlenecks
    H2transportbottleneckA = H2transportneedA - installedH2transportcapacityA
    H2transportbottleneckB = H2transportneedB - installedH2transportcapacityB
    H2transportbottleneckC = H2transportneedC - installedH2transportcapacityC
    H2transportbottleneckD = H2transportneedD - installedH2transportcapacityD

    BotNlist = [0, 0, 0, 0]
    x = 0
    for i in {H2transportbottleneckA, H2transportbottleneckB,
                  H2transportbottleneckC, H2transportbottleneckD}:
        if i > 0:
            BotNlist[x] = True
            x = x+1
        else:
            BotNlist[x] = False
            x = x+1

    # propose investments if needed
    proposedInvestments = []

    # Bottleneck combinations
    BNcomb = [[True, False, False, False],
              [False, True, False, False],
              [False, False, True, False],
              [False, False, False, True],
              [True, True, False, False],
              [True, False, True, False],
              [True, False, False, True],
              [False, True, True, False],
              [False, True, False, True],
              [False, False, True, True],
              [True, True, True, False],
              [False, True, True, True],
              [True, True, False, True],
              [True, False, True, True],
              [True, True, True, True],
              [False, False, False, False]]

    for i in range(len(BNcomb)):
        if BotNlist == BNcomb[i]:
            index = i

    investSetDF2 = InvestSetsDF[InvestSetsDF['SolSetIndex'] == index]

    for row in investSetDF2.iterrows():
        index, data = row
        proposedInvestments.append(data.tolist())

    for i in range(len(proposedInvestments)):
        for row in (InvestID[InvestID['InvestID'] == proposedInvestments[i][1]]).iterrows():
            index, data = row
            for x in data.tolist():
                proposedInvestments[i].append(x)

    defproposedInvestments = []
    for investment in proposedInvestments:
        time = investment[6+decisionMakingModel]
        if time > 0:
            defproposedInvestments.append([investment[1],
                                           investment[10],
                                           int(investment[12]),
                                           int(investment[5]),
                                           year + round(int(time)),
                                           investment[2],
                                           int(investment[3]),
                                           0, 0, investment[1], 1])

    keep = []
    taboo_values = set()

    for investment in defproposedInvestments:
        # investment[5] depencendy between elements of a package of investments
        if investment[0] == 'GTSgrid1H2' and amountGasDemand1D > 0:
            taboo_values.add(investment[5])
            continue
        elif investment[0] == 'GTSgrid2H2' and amountGasDemand2C > 0:
            taboo_values.add(investment[5])
            continue
        elif investment[0] == 'GTSgrid3H2' and amountGasDemand3C > 0:
            taboo_values.add(investment[5])
            continue
        else:
            keep.append(investment)

    keep = [i for i in keep if i[5] not in taboo_values]

    return keep


# @profile
def get_current_infra_status_gas(year):
    # this function returns [total capacity, total demand, year]
    totalCap = dfCap[year].sum()

    df = assetsDict[year]
    H2demandb1 = df.iloc[:, 2] == 'D34'
    H2demandb2 = df.iloc[:, 28] == 'ChangecurrentH2demandb'
    assetsH2demandb = df[H2demandb1 | H2demandb2]
    H2demandc1 = df.iloc[:, 28] == 'ChangecurrentH2demandc'
    H2demandc2 = df.iloc[:, 2] == 'D34'
    assetsH2demandc = df[H2demandc1 | H2demandc2]
    H2demandd1 = df.iloc[:, 28] == 'ChangecurrentH2demandd'
    assetsH2demandd = df[H2demandd1]
    H2demande1 = df.iloc[:, 2] == 'D36'
    assetsH2demande = df[H2demande1]

    amountH2demandB = assetsH2demandb["H2demand"].sum()
    amountH2demandC = assetsH2demandc["H2demand"].sum()
    amountH2demandD = assetsH2demandd["H2demand"].sum()
    amountH2demandE = assetsH2demande["H2demand"].sum()

    # import and export are ignored in this function
    totalDemand = amountH2demandB + amountH2demandC + \
        amountH2demandD + amountH2demandE
    ABMreturn = [totalCap, totalDemand, year]

    return ABMreturn


def invest_gas(investmentID, year):
    # buildingtime for different modi
    # (0,1,2,3) (reactive, current, proactive, collaborative)
    modus = decisionMakingModel
    InvestID = investment_id
    index = InvestID.index[InvestID['InvestID'] == investmentID].tolist()

    if investmentID == "GTSgrid3proactH2":
        GTSgrid3switch = True

    buildingTime = InvestID.iloc[index, modus+2]
    if math.isnan(buildingTime) == False:
        for i in range(year+int(buildingTime), endyear, 1):
            dfCap[i][index] = dfCap[i][index] + dfCap['size 1 link'][index]
        return True
    else:
        return False


def remove_gas_asset(assetID):
    for i in range(year, endyear):
        df = assetsDict[i]
        assetsDict[i] = df[df.iloc[:, 2] != assetID]
    return True


def handle_investment(investment):
    node, edge = investment[7:9]
    assetid = investment[0]

    #
    # investment = [assetid, owner, aditional_overcapacity,
    #               capex, yearFinished, investmentSet,
    #               investmentOptionSet, 1, 0, invesmentID, number_building_blocks]

    if node:
        node = electricity_grid.nodes[assetid]

        try:
            investID = node['InvestID_electricity']
        except KeyError:
            print(node)
            raise
            
        row = investment_id[investment_id.iloc[:, 0] == investID]
        if row.empty:
            # TODO:: this is an error, but unclear how to link investments to
            # assets
            
            investID = stations[stations.iloc[:,2]==assetid].iloc[0,-1]

            row = investment_id[investment_id.iloc[:, 0] == investID]
            if row.empty:
                print(f"{assetid} {investID} {investment}")
                return 
        
        
        blocksize = row.iat[0, 8]
        n_building_blocks = investment[-1]
        additional_capacity = n_building_blocks * blocksize

        try:
            node['capacity'] += additional_capacity
        except KeyError:
            print(f'assedid: {assetid}')
            print(f'node: {node}')
            raise

    elif edge:
        start, stop = investment[0]
        n_blocks = investment[-1]
        id = investment[-2]  # @ReservedAssignment
        row = investment_id[investment_id.iloc[:, 0] == id]
        blocksize = row.iat[0, 8]

        additional_capacity = n_blocks * blocksize

        try:
            existing_capacity = nx.get_edge_attributes(
                electricity_grid, 'Maximum capacity link [MW]')[start, stop]
        except KeyError:
            start, stop = stop, start

            existing_capacity = nx.get_edge_attributes(
                    electricity_grid, 'Maximum capacity link [MW]')[start, stop]

        new_capacity = existing_capacity + additional_capacity

        nx.set_edge_attributes(electricity_grid, {(start, stop): {
                               'Maximum capacity link [MW]': new_capacity}})
    else:
        raise Exception(("node and edge field in investment both False, "
                         "should not happen"))


def implement_egrid_investments(investments):
    # update electricity grid based on investemnt

    for investment in investments:
        try:
            handle_investment(investment)
        except Exception as e:
            print(f"{investment} causes {type(e)} error")
            raise


# @profile
def update_electricity_network(event, network):
    # change a conversion asset based on exogenous event
    
    assetid, assettype, technology, _, amount = event

    if amount == -1:
        amount = 0
    if (assettype == -1) & (technology == -1):
        return

    if 'C1' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D1': {'demand/production': network.node['D1']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C1'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D1': {'demand/production': network.node['D1']['demand/production'] + amount}})
    if 'C2' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D3': {'demand/production': network.node['D3']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C2'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D3': {'demand/production': network.node['D3']['demand/production'] + amount}})
    if 'C10' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C10'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D4': {'demand/production': network.node['D4']['demand/production'] + amount}})
    if 'C11' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C11'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D4': {'demand/production': network.node['D4']['demand/production'] + amount}})
    if 'C12' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C12'].iloc[0][15])}})
    if 'C7' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C7'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D4': {'demand/production': network.node['D4']['demand/production'] + amount}})
    if 'C8' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C8'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D4': {'demand/production': network.node['D4']['demand/production'] + amount}})
    if 'C9' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D4': {'demand/production': network.node['D4']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C11'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D4': {'demand/production': network.node['D4']['demand/production'] + amount}})
    if 'C14' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D5': {'demand/production': network.node['D5']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C14'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {
                                   'D5': {'demand/production': network.node['D5']['demand/production'] + amount}})
    if 'C16' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D6': {'demand/production': network.node['D6']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C16'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D6': {'demand/production': network.node['D6']['demand/production'] + amount}})
    if 'C15' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D6': {'demand/production': network.node['D6']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C15'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {
                                   'D6': {'demand/production': network.node['D6']['demand/production'] + amount}})
    if 'C20' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C20'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C21' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C21'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C22' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C22'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C17' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C17'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C18' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C18'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C19' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D7': {'demand/production': network.node['D7']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C19'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D7': {'demand/production': network.node['D7']['demand/production'] + amount}})
    if 'C23' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D8': {'demand/production': network.node['D8']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C23'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {
                                   'D8': {'demand/production': network.node['D8']['demand/production'] + amount}})
    if 'C24' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D9': {'demand/production': network.node['D9']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C24'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {
                                   'D9': {'demand/production': network.node['D9']['demand/production'] + amount}})
    if 'C25' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D10': {'demand/production': network.node['D10']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C25'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D10': {
                                   'demand/production': network.node['D10']['demand/production'] + amount}})
    if 'C27' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D11': {'demand/production': network.node['D11']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C27'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D11': {
                                   'demand/production': network.node['D11']['demand/production'] + amount}})
    if 'C26' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D11': {'demand/production': network.node['D11']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C26'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D11': {
                                   'demand/production': network.node['D11']['demand/production'] + amount}})
    if 'C28' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D12': {'demand/production': network.node['D12']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C28'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D12': {
                                   'demand/production': network.node['D12']['demand/production'] + amount}})
    if 'C25' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D10': {'demand/production': network.node['D10']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C25'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D10': {
                                   'demand/production': network.node['D10']['demand/production'] + amount}})
    if 'C29' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D13': {'demand/production': network.node['D13']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C29'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D13': {
                                   'demand/production': network.node['D13']['demand/production'] + amount}})
    if 'C30' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D13': {'demand/production': network.node['D13']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C30'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D13': {
                                   'demand/production': network.node['D13']['demand/production'] + amount}})
    if 'C36' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D13': {'demand/production': network.node['D13']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C36'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D13': {
                                   'demand/production': network.node['D13']['demand/production'] + amount}})
    if 'C33' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D14': {'demand/production': network.node['D14']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C33'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D14': {
                                   'demand/production': network.node['D14']['demand/production'] + amount}})
    if 'C34' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D17': {'demand/production': network.node['D17']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C34'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D17': {
                                   'demand/production': network.node['D17']['demand/production'] + amount}})
    if 'C35' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D18': {'demand/production': network.node['D18']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C35'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D18': {
                                   'demand/production': network.node['D18']['demand/production'] + amount}})
    if 'C33' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D14': {'demand/production': network.node['D14']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C33'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D14': {
                                   'demand/production': network.node['D14']['demand/production'] + amount}})
    if 'C37' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D19': {'demand/production': network.node['D19']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C37'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D19': {
                                   'demand/production': network.node['D19']['demand/production'] + amount}})
    if 'C39' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D21': {'demand/production': network.node['D21']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C39'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D21': {
                                   'demand/production': network.node['D21']['demand/production'] + amount}})
    if 'C41' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D22': {'demand/production': network.node['D22']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C41'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D22': {
                                   'demand/production': network.node['D22']['demand/production'] + amount}})
    if 'C42' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D22': {'demand/production': network.node['D22']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C42'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D22': {
                                   'demand/production': network.node['D22']['demand/production'] + amount}})
    if 'C43' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D23': {'demand/production': network.node['D23']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C43'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D23': {
                                   'demand/production': network.node['D23']['demand/production'] + amount}})
    if 'C45' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D24': {'demand/production': network.node['D24']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C45'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D24': {
                                   'demand/production': network.node['D24']['demand/production'] + amount}})
    if 'C44' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D24': {'demand/production': network.node['D24']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C44'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D24': {
                                   'demand/production': network.node['D24']['demand/production'] + amount}})
    if 'C47' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D25': {'demand/production': network.node['D25']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C47'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D25': {
                                   'demand/production': network.node['D25']['demand/production'] + amount}})
    if 'C50' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D26': {'demand/production': network.node['D26']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C50'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D26': {
                                   'demand/production': network.node['D26']['demand/production'] + amount}})
    if 'C51' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D26': {'demand/production': network.node['D26']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C51'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D26': {
                                   'demand/production': network.node['D26']['demand/production'] + amount}})
    if 'C51' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D26': {'demand/production': network.node['D26']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C51'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D26': {
                                   'demand/production': network.node['D26']['demand/production'] + amount}})
    if 'C52' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D26': {'demand/production': network.node['D26']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C52'].iloc[0][15]) + amount) / (0.49*0.85))}})
        else:
            nx.set_node_attributes(network, {'D26': {
                                   'demand/production': network.node['D26']['demand/production'] + amount}})
    if 'C53' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D27': {'demand/production': network.node['D27']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C53'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D27': {
                                   'demand/production': network.node['D27']['demand/production'] + amount}})
    if 'C54' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D28': {'demand/production': network.node['D28']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C54'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D28': {
                                   'demand/production': network.node['D28']['demand/production'] + amount}})
    if 'C55' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D28': {'demand/production': network.node['D28']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C55'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D28': {
                                   'demand/production': network.node['D28']['demand/production'] + amount}})
    if 'C56' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D29': {'demand/production': network.node['D29']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C56'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D29': {
                                   'demand/production': network.node['D29']['demand/production'] + amount}})
    if 'C57' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D30': {'demand/production': network.node['D30']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C57'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D30': {
                                   'demand/production': network.node['D30']['demand/production'] + amount}})
    if 'C58' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D31': {'demand/production': network.node['D31']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C58'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D31': {
                                   'demand/production': network.node['D31']['demand/production'] + amount}})
    if 'C59' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D32': {'demand/production': network.node['D32']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C59'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D32': {
                                   'demand/production': network.node['D32']['demand/production'] + amount}})
    if 'C69' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C69'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C70' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C70'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C71' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C71'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C72' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C72'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C73' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C73'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C74' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + amount + int(
                conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C74'].iloc[0][15])}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C63' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C63'].iloc[0][15]) + amount) / (0.62*0.85))}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C64' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'D33': {'demand/production': network.node['D33']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C64'].iloc[0][15]) + amount) / (0.62*0.85))}})
        else:
            nx.set_node_attributes(network, {'D33': {
                                   'demand/production': network.node['D33']['demand/production'] + amount}})
    if 'C5' in assetid:
        nx.set_node_attributes(network, {'C4': {'demand/production': network.node['C4']['demand/production'] + int(
            conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C5'].iloc[0][15])}})
    if 'C4' in assetid:
        if (technology < 3):
            nx.set_node_attributes(network, {'C4': {'demand/production': network.node['C4']['demand/production'] + (
                (int(conversionAssets_elec[conversionAssets_elec.iloc[:, 2] == 'C4'].iloc[0][15]) + amount) / (0.49*0.85))}})

    if 'C76' in assetid:
        nx.set_node_attributes(network, {'TenneT380MV_trans': {
                               'demand/production': network.node['TenneT380MV_trans']['demand/production'] + (int(all_assets[all_assets.iloc[:, 2] == 'C76'].iloc[0][15])/0.75)}})
    if 'D34' in assetid:
        nx.set_node_attributes(network, {'TenneT380MV_trans': {
                               'demand/production': network.node['TenneT380MV_trans']['demand/production'] + amount}})
    if 'C79' in assetid:
        nx.set_node_attributes(network, {'TenneT380Simonsh_trans': {
                               'demand/production': network.node['TenneT380Simonsh_trans']['demand/production'] + (int(all_assets[all_assets.iloc[:, 2] == 'C79'].iloc[0][15])/0.75)}})
    if 'D35' in assetid:
        nx.set_node_attributes(network, {'TenneT380Simonsh_trans': {
                               'demand/production': network.node['TenneT380Simonsh_trans']['demand/production'] + amount}})
    if ('C40' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C40': {'demand/production': network.node['C40']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C40'].iloc[0][16] * -1)}})
    if ('C66' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C66': {'demand/production': network.node['C66']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C66'].iloc[0][16] * -1)}})
    if ('C67' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C67': {'demand/production': network.node['C67']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C67'].iloc[0][16] * -1)}})
    if ('C68' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C68': {'demand/production': network.node['C68']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C68'].iloc[0][16] * -1)}})
    if ('C3' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C3': {'demand/production': network.node['C3']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C3'].iloc[0][16] * -1)}})
    if ('C6' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C6': {'demand/production': network.node['C6']['demand/production'] + (
            amount * all_assets[all_assets.iloc[:, 2] == 'C6'].iloc[0][16] * -1)}})
    if ('C13' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C13': {'demand/production': (
            amount * all_assets[all_assets.iloc[:, 2] == 'C13'].iloc[0][16] * -1)}})
    if ('C60' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C60': {'demand/production': (
            amount * all_assets[all_assets.iloc[:, 2] == 'C60'].iloc[0][16] * -1)}})
    if ('C61' in assetid and amount != 0):
        nx.set_node_attributes(network, {'C61': {'demand/production': (
            amount * all_assets[all_assets.iloc[:, 2] == 'C61'].iloc[0][16] * -1)}})
    if ('S2' in assetid and amount != 0):
        nx.set_node_attributes(
            network, {'S2': {'demand/production': (amount*-1)}})
    if ('S3' in assetid and amount != 0):
        nx.set_node_attributes(
            network, {'S3': {'demand/production': (amount*-1)}})
    if ('S4' in assetid and amount != 0):
        nx.set_node_attributes(
            network, {'S4': {'demand/production': (amount*-1)}})


# @profile
def allocate_electricity_demand(network):
    restofNL = 0

    for k in tennet150_stations:
        tennet150_demand = 0
        neighbors = set(list(network.neighbors(k)))

        for g in neighbors:
            for i in stedin_stations:
                net_peak_electricity_demand = 0

                if i in neighbors:
                    for j in network.neighbors(i):
                        if 'C' in j:
                            net_peak_electricity_demand += network.nodes[j]['demand/production']
                        if 'D' in j:
                            net_peak_electricity_demand += network.nodes[j]['demand/production']

                            for m in network.neighbors(j):
                                if 'C' in m:
                                    net_peak_electricity_demand += network.nodes[m]['demand/production']
                    nx.set_node_attributes(
                        network, {i: {'demand/production': (net_peak_electricity_demand * 0.8)}})
            if ('C' in g or 'D' in g or 'Stedin' in g):
                tennet150_demand += network.node[g]['demand/production']
            nx.set_node_attributes(
                network, {k: {'demand/production': tennet150_demand}})
        restofNL = restofNL + (tennet150_demand/0.8)

    for nodeid in ['S2', 'S3', 'S4', 'C3', 'C6', 'C13', 'C60', 'C61']:
        try:
            value = network.node[nodeid]['demand/production']
        except KeyError:
            pass
        else:
            restofNL += value

    nx.set_node_attributes(network, {'S5': {'demand/production': restofNL}})

    for t in tennet380_stations:
        tennet380_demand = 0
        for u in network.neighbors(t):
            if ('C' in u or 'S2' in u or 'S3' in u or 'S4' in u or 'S5' in u):
                tennet380_demand += network.node[u]['demand/production']
        nx.set_node_attributes(
            network, {t: {'demand/production':  (tennet380_demand * 0.8)}})

    source_lengths_dict = defaultdict(dict)
    shortest_paths = defaultdict(dict)
    for e in sink_stations:
        if ('trans' in e or e == 'TenneT380restNL_line'):
            if (network.node[e]['demand/production'] > 0):
                for g in network:
                    if 'TenneT' in g and '_' in g:
                        # TODO::ADD ''TenneT380restNL_line''
                        if (g is not 'TenneT380restNL_line' and network.node[g]['demand/production'] < 0):
                            shortest_path = nx.shortest_path(network, e, g,
                                                             'Linelengths_km')
                            shortest_path_length = nx.shortest_path_length(network, e, g,
                                                                           'Linelengths_km')
                            source_lengths_dict[e][g] = shortest_path_length
                            shortest_paths[e][g] = shortest_path

    dp_edges = nx.get_edge_attributes(network, 'demand/production')
    for e, source_lengths in source_lengths_dict.items():
        sum_inverse_values = sum(
            1/v for v in source_lengths.values() if v != 0)
        for g, source_length in source_lengths.items():

            length_weight = ((1/source_length) / sum_inverse_values) * \
                abs(network.node[e]['demand/production'])
            shortest_path = shortest_paths[e][g]

            for start, stop in zip(shortest_path[:-1], shortest_path[1::]):
                try:
                    dp_ratio = dp_edges[start, stop]
                except KeyError:
                    start, stop = stop, start
                    dp_ratio = dp_edges[start, stop]

                nx.set_edge_attributes(
                    network, {(start, stop): {'demand/production': dp_ratio+length_weight}})

            for c in shortest_path:
                dp = network.node[c]['demand/production']
                nx.set_node_attributes(
                    network, {c: {'demand/production': (dp+length_weight)}})


# @profile
def get_needed_electricity_investments(demandExpectations):
    '''

    Returns
    -------
    list 
        list of investments

    '''
    network = electricity_grid.copy()

    for event in demandExpectations:
        try:
            update_electricity_network(event, network)
        except KeyError:
            print(f"event causing error: {event}")
            raise

    allocate_electricity_demand(network)

    neededInvestment = []
    investmentOptionSet = 0
    investmentSet = 0

    for node in stations.iloc[:, 2].values:
        try:
            node = network.nodes[node]
        except KeyError:
            # node has been removed
            # TODO:: stations should be updated when assests are removed
#             print(f"{node} from stations not in network")
            continue

#         print(node)
#         print(node['demand/production'])
#         print(node['capacity'])

        if abs(node['demand/production']) > node['capacity']:
            overcapacity = node['demand/production'] - node['capacity']
            assetid = node['assetID']
            
            try:
                investID = node['InvestID_electricity']
            except KeyError:
                print(node)
                raise
                
            investment_row = investment_id[investment_id.iloc[:, 0] == investID]
            if investment_row.empty:
                # TODO:: this is an error, but unclear how to link investments to
                # assets
                
                investID = stations[stations.iloc[:,2]==assetid].iloc[0,-1]

                investment_row = investment_id[investment_id.iloc[:, 0] == investID]
                if investment_row.empty:
                    print(f"{assetid} {investID}")
                    continue

            construction_time = investment_row.iloc[0, 2+decisionMakingModel]

            building_blocks_size = investment_row.iloc[0, 8]
            number_building_blocks = math.ceil(
                overcapacity/building_blocks_size)

            capex = number_building_blocks * investment_row.iloc[0, 1]
            invesmentID = investment_row.iloc[0, 0]
            owner = investment_row.iloc[0, 6]
            aditional_overcapacity = (
                number_building_blocks - (overcapacity/building_blocks_size)) * building_blocks_size
            yearFinished = year + construction_time

            investment = [assetid, owner, aditional_overcapacity,
                          capex, yearFinished, investmentSet,
                          investmentOptionSet, 1, 0, invesmentID, number_building_blocks]

            investmentOptionSet += 1

            neededInvestment.append(investment)

    for y in network.edges():
        if nx.get_edge_attributes(network, 'demand/production')[y] > nx.get_edge_attributes(network, connectionLinks_elec.columns.values[4])[y]:
            try:
                overcapacity = nx.get_edge_attributes(network, 'demand/production')[
                    y] - nx.get_edge_attributes(network, connectionLinks_elec.columns.values[4])[y]
                line_id = nx.get_edge_attributes(
                    network, connectionLinks_elec.columns.values[0])[y]
                construction_time = investment_id[investment_id.iloc[:, 0]
                                                  == line_id].iloc[0, decisionMakingModel+2]
                building_blocks_size = investment_id[investment_id.iloc[:, 0]
                                                     == line_id].iloc[0, 8]
                number_building_blocks = math.ceil(
                    overcapacity/building_blocks_size)
                capex = number_building_blocks * \
                    investment_id[investment_id.iloc[:, 0]
                                  == line_id].iloc[0, 1]
                invesmentID = investment_id[investment_id.iloc[:, 0]
                                            == line_id].iloc[0, 0]
                owner = investment_id[investment_id.iloc[:, 0]
                                      == line_id].iloc[0, 6]
                additioanal_overcap = (
                    number_building_blocks - overcapacity/building_blocks_size) * building_blocks_size
                yearFinished = year + construction_time

                # TODO:: invesmentID moet nutting zijn (edge definierent)
                investment = [y, owner, additioanal_overcap, capex,
                              yearFinished, investmentSet, investmentOptionSet,
                              0, 1, invesmentID, number_building_blocks]

                investmentOptionSet += 1
                neededInvestment.append(investment)
            except:
                # FIXME::
                pass
    return neededInvestment


# @profile
def asset_change_is_feasible(event, network):
    '''evaluate whether event can be implemented

    Parameters
    ----------
    event : list
    network : nx.Graph


    Returns
    ------
    bool

    '''

    update_electricity_network(event, network)
    allocate_electricity_demand(network)

    for node in network.nodes():
        try:
            if abs(node['demand/production']) > node['capacity']:
                return False
        except:
            pass

    # TODO:: should be possible to return attributes as part of iterations
    for edge in network.edges():
        if nx.get_edge_attributes(network, 'demand/production')[edge] > \
           nx.get_edge_attributes(network, connectionLinks_elec.columns.values[4])[edge]:
            return False

    return True


def change_egrid_asset(event):
    update_electricity_network(event, electricity_grid)
    allocate_electricity_demand(electricity_grid)

#===========================
#
# public interface functions
#
#===========================

def changeAsset(event):
    e_possible = asset_change_is_feasible(event, electricity_grid.copy())
    g_possible = change_gas_asset_demand([event], True)

    if e_possible:
        change_egrid_asset(event)
    if g_possible:
        # TODO:: make change e-grid and g-grid behave in the same way
        pass

    if e_possible and g_possible:
        return True
    else:
        # print(f"{year}: failed {event}")
        return False


def stedinsLostCustomersThisYear():
    global lost_stedin_customers
    for k in tennet150_stations:
        tennet150_demand = 0
        for g in electricity_grid.neighbors(k):
            for i in stedin_stations:
                if i in electricity_grid.neighbors(k):
                    for j in electricity_grid.neighbors(i):
                        if ('D' in j and 'Stedin' not in electricity_grid.nodes[j]['description']):
                            tennet150_demand = tennet150_demand + \
                                electricity_grid.nodes[j]['demand/production']
                            current_lost = [item[0]
                                            for item in lost_stedin_customers]
                            if (electricity_grid.nodes[j]['demand/production'] > 40 and j not in current_lost):
                                lost_customer = [j,
                                                 electricity_grid.nodes[j]['description'],
                                                 electricity_grid.nodes[j]['demand/production'],
                                                 year]
                                lost_stedin_customers += [lost_customer]

    return lost_stedin_customers  # lists of list


def determineImportExportGas():
#    print(" in determineImportExportGas")

    df = assetsDict[year]

    H2demandb1 = df.iloc[:, 2] == 'D34'
    H2demandb2 = df.iloc[:, 28] == 'ChangecurrentH2demandb'
    assetsH2demandb = df[H2demandb1 | H2demandb2]
    H2demandc1 = df.iloc[:, 28] == 'ChangecurrentH2demandc'
    H2demandc2 = df.iloc[:, 2] == 'D35'
    assetsH2demandc = df[H2demandc1 | H2demandc2]
    H2demandd1 = df.iloc[:, 28] == 'ChangecurrentH2demandd'
    assetsH2demandd = df[H2demandd1]
    H2demande1 = df.iloc[:, 2] == 'D36'
    assetsH2demande = df[H2demande1]
    amountH2demandB = assetsH2demandb["H2demand"].sum()
    amountH2demandC = assetsH2demandc["H2demand"].sum()
    amountH2demandD = assetsH2demandd["H2demand"].sum()
    amountH2demandE = assetsH2demande["H2demand"].sum()

    # determine supply and import and export
    H2supplyMV1 = df.iloc[:, 2] == 'C75'
    H2supplyMV2 = df.iloc[:, 2] == 'C76'
    importexport = df.iloc[:, 2] == 'C77'
    assetsH2supplyMV = df[H2supplyMV1 | H2supplyMV2]
    assetsH2importexport = df[importexport]

    H2supplyBotlek1 = df.iloc[:, 2] == 'C78'
    H2supplyBotlek2 = df.iloc[:, 2] == 'C79'
    assetsH2supplyBotlek = df[H2supplyBotlek1 | H2supplyBotlek2]

    amountH2supplyMV = assetsH2supplyMV["H2demand"].sum()
    amountH2supplyBotlek = assetsH2supplyBotlek["H2demand"].sum()
    amountH2ImportExport = (amountH2supplyMV + amountH2supplyBotlek) - (amountH2demandB + amountH2demandC +
                                                                        amountH2demandD + amountH2demandE)

    if amountH2ImportExport < 0:
        amountH2ImportExport = 0

#    print(f"amount {amountH2ImportExport}")

    return amountH2ImportExport


def setCurrentYear(y):
    global year
    year = y
#     print(year)

    implement_egrid_investments(staged_investments[year])


# @profile
def getNeededInfrastructureInvestmentsIfTheseEventsHappen(demandExpectations):

    #!! dummy states that event is list [assedID, aset type, asset type
    #!! technology, year, volume]
    #!! description below states something different

    # netlogo will set a variable  demandExpectations , which is a list  of list:
    # [["InfraProviderName", AssetID that will change, assetTypeIndex,
    # assetTechnologyTypeIndex, Year when  it will happen,amount] [...] [...] ]
    # should return : [investmentID, owner name, MWAdditionalOvercapacity,
    # MEUR CAPEX, yearFinished, investmentSet, investmentOptionSet ]
    # investmentOption is a uniqe ID that all alternatives for this investment
    # have investmentSet a unique identifier of a group of alternative
    # equivalen investment groups Electricity

    investments_electricity = get_needed_electricity_investments(demandExpectations)
    investments_gas = get_needed_gas_investments(demandExpectations)
    needed_investments = investments_electricity + investments_gas

#     print(f"[{year}] needed investments:")
#     for i in needed_investments:
#         print(f"{i}")

    return needed_investments


# @profile
def makeInfrastructureInvestment(makeThisInvestment):
    investmentID = makeThisInvestment[0]

    # GAS#       !! investmentID must be string !!
    if investmentID in ['NewH2grid1a', 'NewH2grid1b', 'NewH2grid1c', 'NewH2grid1d',
                        'GTSgrid1H2', 'GTSgrid2H2', 'GTSgrid3H2', 'GTSgrid3proactH2',
                        'NewH2grid2', 'NewH2grid3']:
        return invest_gas(investmentID, year)  # returns True
    else:
        year_completed = makeThisInvestment[4]
        staged_investments[year_completed].append(makeThisInvestment)
    # returns True upon successful investment. It should never return False.
    return True


def getScenario():

    # makes scenario the same so easier to debug
    random.seed(123456789)

    events = [[random.choice(all_assets.iloc[:, 2]), random.randint(0, 4),
               random.randint(0, 4), random.randint(2020, 2050),
               random.randint(-1, 200)] for _ in range(random.randint(0, 40))]
#     events.insert(0, ['C3', -1, -1, 2021, -1])

    events = [('C1', 0, 0, 2024, -1), ('C1', 0, 1, 2028, -1), ('C2', 0, 0, 2021, -1), ('C2', 0, 1, 2025, -1),
              ('C5', 0, 0, 2021, -1), ('C5', 0, 1, 2025, -
                                       1), ('C10', 0, 0, 2024, -1), ('C10', 0, 1, 2028, -1),
              ('C11', 0, 0, 2025, -1), ('C11', 0, 1, 2029, -
                                        1), ('C12', 0, 0, 2023, -1), ('C12', 0, 1, 2027, -1),
              ('C16', 0, 0, 2022, -1), ('C16', 0, 1, 2026, -
                                        1), ('C20', 0, 0, 2020, -1), ('C20', 0, 1, 2024, -1),
              ('C21', 0, 0, 2020, -1), ('C21', 0, 1, 2024, -
                                        1), ('C22', 0, 0, 2022, -1), ('C22', 0, 1, 2026, -1),
              ('C24', 0, 0, 2021, -1), ('C24', 0, 1, 2025, -
                                        1), ('C25', 0, 0, 2020, -1), ('C25', 0, 1, 2024, -1),
              ('C27', 0, 0, 2020, -1), ('C27', 0, 1, 2024, -
                                        1), ('C28', 0, 0, 2023, -1), ('C28', 0, 1, 2027, -1),
              ('C33', 0, 0, 2023, -1), ('C33', 0, 1, 2027, -
                                        1), ('C34', 0, 0, 2024, -1), ('C34', 0, 1, 2028, -1),
              ('C35', 0, 0, 2023, -1), ('C35', 0, 1, 2027, -
                                        1), ('C43', 0, 0, 2020, -1), ('C43', 0, 1, 2024, -1),
              ('C45', 0, 0, 2021, -1), ('C45', 0, 1, 2025, -
                                        1), ('C50', 0, 0, 2025, -1), ('C50', 0, 1, 2029, -1),
              ('C53', 0, 0, 2025, -1), ('C53', 0, 1, 2029, -
                                        1), ('C56', 0, 0, 2024, -1), ('C56', 0, 1, 2028, -1),
              ('C58', 0, 0, 2021, -1), ('C58', 0, 1, 2025, -
                                        1), ('C59', 0, 0, 2024, -1), ('C59', 0, 1, 2028, -1),
              ('C69', 0, 0, 2025, -1), ('C69', 0, 1, 2029, -
                                        1), ('C70', 0, 0, 2024, -1), ('C70', 0, 1, 2028, -1),
              ('C71', 0, 0, 2022, -1), ('C71', 0, 1, 2026, -
                                        1), ('C7', 1, 2, 2031, -1), ('C8', 1, 2, 2032, -1),
              ('C9', 1, 2, 2030, -1), ('C17', 1, 2, 2034, -
                                       1), ('C18', 1, 2, 2032, -1), ('C19', 1, 2, 2035, -1),
              ('C26', 1, 2, 2030, -1), ('C39', 1, 2, 2032, -
                                        1), ('C41', 1, 2, 2034, -1), ('C42', 1, 2, 2031, -1),
              ('C47', 1, 2, 2034, -1), ('C51', 1, 2, 2033, -
                                        1), ('C54', 1, 2, 2034, -1), ('C55', 1, 2, 2030, -1),
              ('C57', 1, 2, 2030, -1), ('C72', 1, 2, 2033, -
                                        1), ('C73', 1, 2, 2033, -1), ('C74', 1, 2, 2033, -1),
              ('C4', 2, 3, 2026, -1), ('C14', 2, 3, 2026, -
                                       1), ('C15', 2, 3, 2028, -1), ('C23', 2, 3, 2028, -1),
              ('C29', 2, 3, 2024, -1), ('C30', 2, 3, 2026, -
                                        1), ('C36', 2, 3, 2025, -1), ('C37', 2, 3, 2029, -1),
              ('C44', 2, 3, 2024, -1), ('C52', 2, 3, 2025, -
                                        1), ('C63', 2, 3, 2027, -1), ('C64', 2, 3, 2026, -1),
              ('C31', 3, 0, 2025, -1), ('C31', 3, 1, 2043, -
                                        1), ('C32', 3, 0, 2025, -1), ('C32', 3, 1, 2043, -1),
              ('C48', 3, 0, 2025, -1), ('C48', 3, 1, 2043, -
                                        1), ('C49', 3, 0, 2025, -1), ('C49', 3, 1, 2043, -1),
              ('C62', 3, 0, 2024, -1), ('C62', 3, 1, 2042, -
                                        1), ('C75', 3, 0, 2024, -1), ('C76', 3, 1, 2042, -1),
              ('D35', 4, 0, 2032, -1), ('D35', 4, 0, 2036, -
                                        1), ('D35', 4, 0, 2044, -1), ('C3', -1, -1, 2027, -1),
              ('C6', -1, -1, 2023, -1), ('C40', 6, 0, 2029, -
                                         1), ('C66', 6, 0, 2029, -1), ('C67', 6, 0, 2028, -1),
              ('C68', 6, 0, 2029, -1), ('C13', 7, 0, 2026, -
                                        1), ('C60', 7, 0, 2029, -1), ('C61', 7, 0, 2026, -1),
              ('D36', 9, 0, 2024, 0.04104960916745492), ('D36',
                                                         9, 0, 2025, 0.09132755585961076),
              ('D36', 9, 0, 2026, 0.2031046342506859), ('D36',
                                                        9, 0, 2027, 0.4512834910196794),
              ('D36', 9, 0, 2028, 1.0007324190619449), ('D36',
                                                        9, 0, 2029, 2.2094600618751556),
              ('D36', 9, 0, 2030, 4.83173212654324), ('D36',
                                                      9, 0, 2031, 10.352547916007476),
              ('D36', 9, 0, 2032, 21.275736163240794), ('D36',
                                                        9, 0, 2033, 40.45557567816083),
              ('D36', 9, 0, 2034, 68.0), ('D36', 9, 0, 2035, 97.97259450115135),
              ('D36', 9, 0, 2036, 122.168305610034), ('D36',
                                                      9, 0, 2037, 137.41723690195985),
              ('D36', 9, 0, 2038, 145.58218652173082), ('D36',
                                                        9, 0, 2039, 149.57553562854815),
              ('D36', 9, 0, 2040, 151.44208741004965), ('D36',
                                                        9, 0, 2041, 152.2960375109054),
              ('D36', 9, 0, 2042, 152.68288580076072), ('D36',
                                                        9, 0, 2043, 152.8573485910448),
              ('D36', 9, 0, 2044, 152.93586966407742), ('D36',
                                                        9, 0, 2045, 152.97117772997476),
              ('D36', 9, 0, 2046, 152.98704797567643), ('D36',
                                                        9, 0, 2047, 152.9941800090206),
              ('D36', 9, 0, 2048, 152.99738485470246), ('D36',
                                                        9, 0, 2049, 152.9988249284123),
              ('D37', -1, -1, 2041, -1)]

    print(events)
    return events


# @profile
def getCurrentInfrastructureStatus(nameOfInfraProvider):
    network = electricity_grid
    
    if nameOfInfraProvider == 'Stedin' or nameOfInfraProvider == 'TenneT':
        totalMWcap = 0
        totalMWflow = 0
        for i in network:
#             if nameOfInfraProvider == 'TenneT':
#                 source_lengths_dict = defaultdict(dict)
#                 shortest_paths = defaultdict(dict)
#                 
#                 stations = [s for s in sink_stations if ('trans' in s or s == 'TenneT380restNL_line')]
#                 
#                 for e in stations:
#                     if (network.node[e]['demand/production'] > 0):
#                         for g in network:
#                             if 'TenneT' in g and '_' in g:
#                                 # TODO::ADD ''TenneT380restNL_line''
#                                 if (g is not 'TenneT380restNL_line' and\
#                                     network.node[g]['demand/production'] < 0):
#                                     shortest_path = nx.shortest_path(network, e, g,
#                                                                      connectionLinks_elec.columns.values[8])
#                                     shortest_path_length = nx.shortest_path_length(network, e, g,
#                                                                                    connectionLinks_elec.columns.values[8])
#                                     if shortest_path_length == 0:
#                                         # FIXME:: no idea what is happening in the code here, this avoids crashes
#                                         shortest_path_length = 1
#                         
#                                     source_lengths_dict[e][g] = shortest_path_length
#                                     shortest_paths[e][g] = shortest_path
#   
#                 for e, source_lengths in source_lengths_dict.items():
#                     sum_inverse_values = sum(
#                         1/v for v in source_lengths.values() if v != 0)
#  
#                     if sum_inverse_values == 0:
#                         # FIXME:: no idea what is happening in the code here, this avoids crashes
#                         sum_inverse_values = 1
#  
#                     for g, source_length in source_lengths.items():
#                         length_weight = (
#                             (1/source_length) / sum_inverse_values) * abs(network.node[e]['demand/production'])
#                         shortest_path = shortest_paths[e][g]
#                         for start, stop in zip(shortest_path[1::], shortest_path[:-1]):
#                             try:
#                                 dp_ratio = nx.get_edge_attributes(
#                                     network, 'demand/production')[start, stop]
#                             except KeyError:
#                                 start, stop = stop, start
#                                 dp_ratio = nx.get_edge_attributes(
#                                     network, 'demand/production')[start, stop]
#  
#                             nx.set_edge_attributes(
#                                 network, {(start, stop): {'demand/production':  dp_ratio+length_weight}})
#                         for c in shortest_path:
#                             dp = network.node[c]['demand/production']
#                             nx.set_node_attributes(network, {
#                                                    c: {'demand/production': (dp+length_weight)}})
 
            if (nameOfInfraProvider in i and '_' in i):
                totalMWcap = totalMWcap + network.node[i]['capacity']
                totalMWflow = totalMWflow + \
                    network.node[i]['demand/production']
            for y in network.edges:
                if nameOfInfraProvider in linkOwner[y]:
                    totalMWcap = totalMWcap + linkCapacity[y]
                    try:
                        totalMWflow += nx.get_edge_attributes(
                            network, 'demand/production')[y]
                    except:
                        pass
                 
        if nameOfInfraProvider == 'Stedin':
            if (nameOfInfraProvider in i and 'Steam' not in i):
                totalMWcap = totalMWcap + network.node[i]['capacity']
                totalMWflow = totalMWflow + network.node[i]['demand/production']
            for y in network.edges:
                if nameOfInfraProvider in linkOwner[y]:
                    totalMWcap = totalMWcap + linkCapacity[y]
#         
        infra_status = [totalMWcap, totalMWflow, year]
    elif nameOfInfraProvider == 'GTS':
        infra_status = get_current_infra_status_gas(year)
    elif nameOfInfraProvider == 'random':
        infra_status = [random.randint(3, 100), random.randint(
            1, 40), random.randint(2020, 2050)]
        # ["totalMaxMW capacity"  "total MWs flowing in the system" "year"]
    else:
        raise ValueError(f"unknown infra provider name {nameOfInfraProvider}")
    
#    print(f"{nameOfInfraProvider} {infra_status}")
    
    return infra_status


def resetModel():
    global electricity_grid
    global staged_investments

    staged_investments = defaultdict(list)

    # just to be sure
    connectionLinks_elec = pd.read_csv(
        connectionLinks_file, header=16).fillna(100000)
    logical = (connectionLinks_elec.loc[:, 'Status'] == 'Existing') &\
              (connectionLinks_elec.loc[:, 'Feedstock carried'] == 'Electricity')
    connectionLinks_elec = connectionLinks_elec[logical]

    electricity_grid = nx.from_pandas_edgelist(
        connectionLinks_elec,
        source=connectionLinks_elec.columns.values[1],
        target=connectionLinks_elec.columns.values[2],
        edge_attr=True,
    )

    # 'Feedstocks input for conversion asset – MW, per feedstock, separated by :'
    index = site_demands.iloc[:, 2]
    location = pd.Series(site_demands.iloc[:, 1].values,
                                  index=index)
    status = pd.Series(site_demands.iloc[:, 3].values,
                                index=index)    
    description = pd.Series(site_demands.iloc[:, 12].values,
                                     index=site_demands.iloc[:, 2])
    owner = pd.Series(site_demands.iloc[:, 13].values,
                               index=index)
    demands = pd.Series(site_demands.iloc[:, 15].values.astype(float),
                                 index=index)
    conversion_assets= pd.Series(index.values, index=index)

    nx.set_node_attributes(electricity_grid, demands, 'demand/production')
    nx.set_node_attributes(electricity_grid, description, 'description')
    nx.set_node_attributes(electricity_grid, owner, 'owner')
    nx.set_node_attributes(electricity_grid, location, 'location')
    nx.set_node_attributes(electricity_grid, status, 'status')
    nx.set_node_attributes(electricity_grid, conversion_assets.to_dict(), 'assetID')

    index = conversionAssets_elec.iloc[:, 2]
    production = pd.Series((conversionAssets_elec.iloc[:, 15].astype(int)*\
                            conversionAssets_elec.iloc[:, 16].values * -1).values,
                            index=index     )
    description = pd.Series(conversionAssets_elec.iloc[:, 12].values,
                            index=index)
    owner = pd.Series(conversionAssets_elec.iloc[:, 13].values,
                      index=index)
    location = pd.Series(conversionAssets_elec.iloc[:, 1].values,
                         index=index)
    status = pd.Series(conversionAssets_elec.iloc[:, 3].values,
                       index=index)

    nx.set_node_attributes(electricity_grid, production, 'demand/production')
    nx.set_node_attributes(electricity_grid, description, 'description')
    nx.set_node_attributes(electricity_grid, owner, 'owner')
    nx.set_node_attributes(electricity_grid, location, 'location')
    nx.set_node_attributes(electricity_grid, status, 'status')

    stations_id = stations.iloc[:, 2]
    demand = pd.Series(stations.iloc[:, 17].astype(int).values, index=stations_id)
    capacity = pd.Series(stations.iloc[:, 15].astype(int).values, index=stations_id)
    description = pd.Series(stations.iloc[:, 12].values, index=stations_id)
    owner = pd.Series(stations.iloc[:, 13].values, index=stations_id)
    location = pd.Series(stations.iloc[:, 1].values, index=stations_id)
    status = pd.Series(stations.iloc[:, 3].values, index=stations_id)
    investment_identifier = pd.Series(stations.loc[:, 'InvestID_electricity'].values,
                                      index=stations_id)
    stations_id = pd.Series(stations.iloc[:, 2].values, index=stations_id)

    nx.set_node_attributes(electricity_grid, demand, 'demand/production')
    nx.set_node_attributes(electricity_grid, capacity, 'capacity')
    nx.set_node_attributes(electricity_grid, description, 'description')
    nx.set_node_attributes(electricity_grid, owner, 'owner')
    nx.set_node_attributes(electricity_grid, location, 'location')
    nx.set_node_attributes(electricity_grid, status, 'status')
    nx.set_node_attributes(electricity_grid, stations_id, 'assetID')
    nx.set_node_attributes(electricity_grid, investment_identifier, 'InvestID_electricity')
    

    energysupply_id = energySupply.iloc[:, 2]
    offshoreSupply_dict = pd.Series((energySupply.iloc[:, 15].astype(
        int) * -1).values, index=energysupply_id).to_dict()
    offshoreDescription_dict = pd.Series(
        energySupply.iloc[:, 12].values, index=energysupply_id)
    offshoreLocation_dict = pd.Series(
        energySupply.iloc[:, 1].values, index=energysupply_id)

    nx.set_node_attributes(
        electricity_grid, offshoreSupply_dict, 'demand/production')
    nx.set_node_attributes(
        electricity_grid, offshoreDescription_dict, 'description')
    nx.set_node_attributes(electricity_grid, offshoreLocation_dict, 'location')

    NL_export = sum(pd.Series(site_demands.iloc[:, 15].values.astype(float),
                              index=site_demands.iloc[:, 2]).to_dict().values()) + \
        sum((conversionAssets_elec.iloc[:, 15].astype(int) * conversionAssets_elec.iloc[:, 16].values * -1).values) + \
        (int(energySupply[energysupply_id == 'S2'].iloc[0, 15]) * -1) + \
        (int(energySupply[energysupply_id == 'S3'].iloc[0, 15]) * -1) + \
        (int(energySupply[energysupply_id == 'S4'].iloc[0, 15]) * -1)
    nx.set_node_attributes(
        electricity_grid, {'S5': {'demand/production': NL_export}})

    for t in tennet380_stations:
        tennet380_demand = 0
        for u in electricity_grid.neighbors(t):
            if ('C' in u or 'S2' in u or 'S3' in u or 'S4' in u or 'S5' in u):
                tennet380_demand += electricity_grid.node[u]['demand/production']
        nx.set_node_attributes(
            electricity_grid, {t: {'demand/production': (tennet380_demand * 0.8)}})

    for k in tennet150_stations:
        tennet150_demand = 0
        for g in electricity_grid.neighbors(k):
            for i in stedin_stations:
                net_peak_electricity_demand = 0
                if i in electricity_grid.neighbors(k):
                    for j in electricity_grid.neighbors(i):
                        if 'C' in j:
                            net_peak_electricity_demand += electricity_grid.nodes[j]['demand/production']
                        if 'D' in j:
                            net_peak_electricity_demand = + \
                                electricity_grid.nodes[j]['demand/production']
                            for m in electricity_grid.neighbors(j):
                                if 'C' in m:
                                    net_peak_electricity_demand += electricity_grid.nodes[m]['demand/production']
                    nx.set_node_attributes(electricity_grid, {
                                           i: {'demand/production': (net_peak_electricity_demand * 0.8)}})
            if ('C' in g or 'D' in g or 'Stedin' in g):
                tennet150_demand = tennet150_demand + \
                    electricity_grid.node[g]['demand/production']
            nx.set_node_attributes(
                electricity_grid, {k: {'demand/production': tennet150_demand}})
    return True


def removeAsset(assetID):
    remove_gas_asset(assetID)

    try:
        electricity_grid.remove_node(assetID)
    except NetworkXError:
        pass # node does not exist in egrid network
    return True


resetModel()  # just to be sure everything is initialized
