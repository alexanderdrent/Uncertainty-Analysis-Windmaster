import datetime
import enum
import json
import math
import os
from collections import namedtuple, Counter
import numpy as np
import pandas as pd
from SALib.analyze import sobol

from ema_workbench import (CategoricalParameter, IntegerParameter,
                           BooleanParameter, RealParameter,
                           ema_logging)
from ema_workbench.connectors import netlogo
from ema_workbench.em_framework import get_SALib_problem
from ema_workbench.em_framework.evaluators import MultiprocessingEvaluator, MC, SequentialEvaluator, SOBOL
from ema_workbench.em_framework.outcomes import ArrayOutcome
from ema_workbench.util.ema_exceptions import CaseError
from ema_workbench.util.ema_logging import method_logger, get_module_logger
from ema_workbench.util.utilities import save_results

_logger = get_module_logger(__name__)

def create_event(asset_id, assettype, technology, year, volume=-1):
    return asset_id, assettype.value, technology.value, year, volume


def sigmoid(k, q, b, time):
    '''

    Parameters
    ----------
    k : float
        upper asymptote
    q : float
        effects Y(0)
    b : float
        growth rate
    time:

    '''
    delta = time[-1] - time[0]
    t0_delta = time[0] + 10

    time = [(t - t0_delta) * 20 / delta for t in time]

    a = [k / (1 + q * math.e ** (-b * t)) for t in time]

    return a



class WindMasterModel(netlogo.NetLogoModel):
    startyear = 2020
    start_h2import = 2025
    nticks = 2
    fixed_unc = ["yearGunvorPhaseout",
                 "baseload biomass or closure C3",
                 "baseload biomass or closure C6",
                 "C3 year",
                 "C6 year",
                 "yearKochPhaseout",
                 "yearBPOffline",
                 "yearHydrocrackerBP",
                 "year of introduction ELECTROLYSIS_H20",
                 "easterly demand H2",
                 "year end demand gas Roterdam",
                 "SF factory 2032 location",
                 "SF factory 2036 location",
                 "SF factory 2040 location",
                 "SF factory 2044 location",
                 "SF factory 2048 location",
                 "SMR paths",
                 "location h2 production"
                 ]
    fixed_values_unc = \
        {'C3 year': 2030.0,
         'C6 year': 2025.0,
         'SF factory 2032 location': 'none',
         'SF factory 2036 location': 'maasvlakte',
         'SF factory 2040 location': 'maasvlakte',
         'SF factory 2044 location': 'botlek',
         'SF factory 2048 location': 'maasvlakte',
         'SMR paths': 'SMRTechnologyPaths.SMR_CCS',
         'baseload biomass or closure C3': False,
         'baseload biomass or closure C6': True,
         'easterly demand H2': 76.0,
         'location h2 production': 'none',
         'year end demand gas Roterdam': 2032.0,
         'year of introduction ELECTROLYSIS_H20': 2040.0,
         'yearBPOffline': 2039.0,
         'yearGunvorPhaseout': 2025.0,
         'yearHydrocrackerBP': True,
         'yearKochPhaseout': 2030.0}


    # een event is een tuple van assetID, asset type, asset technology type, year

    @method_logger(__name__)
    def model_init(self, policy):
        netlogo.NetLogoModel.model_init(self, policy)
        for entry in ["provideWarnings?", "verbose?", "debug?"]:
            self.netlogo.command(f"set {entry} false")
        self.netlogo.command("setup")

    @method_logger(__name__)
    def run_experiment(self, experiment):
        for unc in self.fixed_unc:
            experiment[unc] = self.fixed_values_unc[unc]
            if unc == "SMR paths":
                experiment[unc] = eval(self.fixed_values_unc[unc])
        self.netlogo.command("startNewRun")
        # transform experiment to correct order
        # determine year of activation for all feedstocks
        self.yearofintroduction['SMR'].loc["ELECTROLYSIS_H2O"] = experiment["year of introduction ELECTROLYSIS_H20"]
        self.yearofintroduction['SMR'].loc["SMR_CCS"] = experiment["timing CCS"]

        # H2 availability
        # minimum of SMR path availability and import
        start_h2production = self.get_year_of_availability(AssetTypes.SMR,
                                                           experiment[f"{AssetTypes.SMR.name} paths"].value[
                                                               0])
        year_h2 = min(self.start_h2import, start_h2production)
        for value in self.yearofintroduction.values():
            for item in ["HYBRIDH2", "H2"]:
                try:
                    value.loc[item] = year_h2
                except ValueError:
                    pass

        # events
        events = []

        # assettypes with pathways
        for assettype in self.paths.keys():
            assettype = AssetTypes[assettype]
            try:
                path = experiment[f"{assettype.name} paths"]
            except KeyError:
                # print(f"{assettype.name} path not defined")
                continue

            for asset_id in self.assets[assettype.name]:
                delta = experiment[asset_id]

                for bt in path.value:
                    year_of_availability = self.get_year_of_availability(assettype, bt)
                    year = year_of_availability + delta
                    event = create_event(asset_id, assettype, bt, year)
                    events.append(event)

            if assettype.name == "SMR":
                location = experiment["location h2 production"]

                if location == 'maasvlakte':
                    if len(path.value) == 1:
                        year = self.get_year_of_availability(assettype, bt)
                        event = create_event('C76', assettype, path.value[0],
                                             year)
                        events.append(event)
                    else:
                        for bt, asset_id in zip(path.value, ['C75', 'C76']):
                            year = self.get_year_of_availability(assettype, bt)
                            event = create_event(asset_id, assettype, bt, year)
                            events.append(event)
                elif location == 'botlek':
                    if len(path.value) == 1:
                        year = self.get_year_of_availability(assettype, bt)
                        event = create_event('C79', assettype, path.value[0],
                                             year)
                        events.append(event)
                    else:
                        for bt, asset_id in zip(path.value, ['C78', 'C79']):
                            year = self.get_year_of_availability(assettype, bt)
                            event = create_event(asset_id, assettype, bt,
                                                 year)
                            events.append(event)

        assettype = AssetTypes['SyntheticFuelPlant'.upper()]
        FakeTechnology = namedtuple('SFPTechnology', 'value')
        for year in [2032, 2036, 2040, 2044, 2048]:
            location = experiment[f"SF factory {year} location"]
            if location != 'none':
                assetid = SynethicFuelLocationsEnum[location.upper()].value

                event = create_event(assetid, assettype, FakeTechnology(0),
                                     year)
                events.append(event)

        assettype = AssetTypes["Powergen_baseload".upper()]
        for assetid in self.assets[assettype.name]:
            biomass = experiment[f"baseload biomass or closure {assetid}"]
            year = experiment[f"{assetid} year"]
            if biomass:
                event = create_event(assetid, assettype, FakeTechnology(0),
                                     year)
            else:
                event = create_event(assetid, FakeTechnology(-1), FakeTechnology(-1),
                                     year)
            events.append(event)

        for assettype in ["Powergen_baseloadindust", "Powergen_flexible"]:
            assettype = AssetTypes[assettype.upper()]
            for assetid in self.assets[assettype.name]:
                delta = experiment[f"{assetid} delta"]
                year = start_h2production + delta

                event = create_event(assetid, assettype, FakeTechnology(0),
                                     year)
                events.append(event)

        # offshore wind scenarios
        offshore_wind = experiment["offshore wind growth"]
        if offshore_wind:
            time = np.arange(2030, 2050)
            volumes_mv = sigmoid(1300, 0.5, 1, time)  # S2
            volumes_sh = sigmoid(1200, 0.5, 1, time)  # S3

            for year, volume_mv, volume_sh in zip(time, volumes_mv, volumes_sh):
                event_mv = create_event('S2', AssetTypes["WIND"],
                                        FakeTechnology(0), year, volume_mv)
                event_sh = create_event('S3', AssetTypes["WIND"],
                                        FakeTechnology(0), year, volume_sh)

                events.append(event_mv)
                events.append(event_sh)

        # easterly demand H2
        easterly_h2 = experiment["easterly demand H2"]
        time = np.arange(year_h2, 2050)
        volumes = sigmoid(easterly_h2, 1.25, 1, time)
        for year, volume in zip(time, volumes):
            event = create_event('D36', AssetTypes["H2"],
                                 FakeTechnology(0), year, volume)
            events.append(event)

        # end of demand natgas from built environment Rotterdam
        year = experiment["year end demand gas Roterdam"]
        event = create_event('D37', FakeTechnology(-1),
                             FakeTechnology(-1), year)
        events.append(event)

        eventstring = '['
        for event in events:
            eventstring += "[\"{}\" {} {} {} {}]".format(*event)
        eventstring += ']'

        self.netlogo.command(f"set scenario {eventstring}")
        self.netlogo.command("set yearGunvorPhaseout {}".format(experiment["yearGunvorPhaseout"]))
        self.netlogo.command("set yearKochPhaseout {}".format(experiment["yearKochPhaseout"]))

        bp = experiment["yearHydrocrackerBP"]
        if bp:
            self.netlogo.command("set yearHydrocrackerBP 2025")
        else:
            self.netlogo.command("set yearBPOffline {}".format(experiment["yearBPOffline"]))

        dm = experiment["decisionMakingModel"]
        self.netlogo.command(f"set decisionMakingModel \"{dm}\"")
        self.netlogo.command('random-seed {}'.format(experiment["random-seed"]))
        self.netlogo.command("ask infraProviders [set capex_factor {}]".format(experiment["capex_factor"]))
        self.netlogo.command("ask infraProviders [set leadtime_factor {}]".format(experiment["leadtime_factor"]))
        self.netlogo.command(
            "ask infraProviders [set shuffle-needed-investments? {}]".format(experiment["shuffle-needed-investments?"]))

        # run model
        try:
            self.netlogo.command(f"repeat {self.nticks}  [go]")
        except Exception as e:
            raise CaseError(repr(e), experiment)

        # structure: [capacity, use, year]
        scenario_execution = self.netlogo.report('reportRealisedScenarioEvents')
        stedin = self.netlogo.report('stedinCapacityAndLoadOverTime')
        tennet = self.netlogo.report('tennetCapacityAndLoadOverTime')
        gasunie = self.netlogo.report('gtsCapacityAndLoadOverTime')
        investments = self.netlogo.report('investmentsOverTime')
        capex = self.netlogo.report('capexOverTime')
        h2_import = self.netlogo.report('portsideH2OverYears')
        stedin_lost = self.netlogo.report('stedinsLostCustomers')

        scens = []
        for entry in scenario_execution:
            asset = entry[0]
            type = entry[1]
            technology = entry[2]
            year = entry[3]
            entry = (asset, type, technology, year)
            scens.append(entry)
        scenario_execution = scens

        missed = set([e[0:4] for e in events]) - set(scenario_execution)

        missed_per_year = Counter()
        for event in missed:
            year = event[-1]
            missed_per_year[year] += 1
        missed_per_year = [missed_per_year[yr] for yr in range(2020, 2050)]

        # havenzijdige H2 import
        year = 2050
        if missed:
            years = [entry[-1] for entry in missed]
            year = min(years)

        results = {'stedin_capacity': [entry[0] for entry in stedin],
                   'stedin_load': [entry[1] for entry in stedin],
                   'tennet_capacity': [entry[0] for entry in tennet],
                   'tennet_load': [entry[1] for entry in tennet],
                   'gasunie_capacity': [entry[0] for entry in gasunie],
                   'gasunie_load': [entry[1] for entry in gasunie],
                   'first_failure': year,
                   'h2_import': h2_import,
                   "stedin capex": [entry[0] for entry in capex],
                   "tennet capex": [entry[1] for entry in capex],
                   "gasunie capex": [entry[2] for entry in capex],
                   'collaborative capex': [entry[3] for entry in capex],
                   "stedin_lost": stedin_lost,
                   "missed_over_time": missed_per_year
                   }

        for tick in range(0, self.nticks):
            results[f'investments_tick_{tick}'] = investments[tick]

        return results

    def get_year_of_availability(self, assettype, technology):
        data = self.yearofintroduction[assettype.name]
        a = data.loc[technology.name]
        try:
            year = int(a.values[0])
        except ValueError:
            year = 2040

        return year


def create_paths(paths, techEnum, assetTypeName):
    path_mapping = {}

    for path in paths.values:
        path = [entry for (entry, isnnan) in zip(path, pd.isnull(path)) if
                not isnnan]
        path = [techEnum[entry.upper()] for entry in path]

        name = ''
        for entry in path:
            if name:
                name += '_'

            name += entry.name.upper()
        path_mapping[name] = path

    name = "{}TechnologyPaths".format(assetTypeName)
    PathEnum = enum.Enum(name, path_mapping)
    globals()[name] = PathEnum
    return PathEnum


def generate_enums():
    assetTypes = pd.read_csv('../model/prototype/data/assetTypes.csv',
                             header=None)
    AssetTypes = enum.Enum("AssetTypes",
                           {n[0].upper(): i for i, n in enumerate(assetTypes.values)})
    globals()[AssetTypes.__name__] = AssetTypes

    assetTypeTechnologies = pd.read_csv('../model/prototype/data/assetTypeTechnologies.csv',
                                        header=None)
    technologyPaths = pd.read_csv('../model/prototype/data/technologyPaths.csv',
                                  header=None, index_col=0)
    technologyPaths.dropna(how="all", inplace=True)
    technologyPaths.index = [c.upper() for c in technologyPaths.index]

    asset_paths = {}
    for assetType in AssetTypes:
        if assetType.name != 'SMR':
            assetTypeName = assetType.name.lower().capitalize()
            name = f"{assetTypeName}Technologies"
        else:
            assetTypeName = assetType.name
            name = f"{assetTypeName}Technologies"
        values = assetTypeTechnologies.loc[assetType.value, :].dropna().values
        techEnum = enum.Enum(name, {n.upper(): i for i, n in enumerate(values)})

        globals()[name] = techEnum

        try:
            paths = technologyPaths.loc[assetType.name]
        except KeyError:
            continue

        if isinstance(paths, pd.Series):
            continue
        else:
            PathEnum = create_paths(paths, techEnum, assetTypeName)
            asset_paths[assetType.name] = PathEnum

    return asset_paths


def get_assets():
    all_assets = pd.read_csv("../model/prototype/data/conversionAssets.csv",
                             header=17, usecols=["Conversion asset ID [string] – Must be unique",
                                                 "assetTypes"])

    assetids = {}
    for name, group in all_assets.groupby('assetTypes'):
        try:
            assettype = AssetTypes[name.upper()]
        except KeyError:
            pass
        else:
            assetids[assettype.name] = group["Conversion asset ID [string] – Must be unique"].values

    return assetids


def get_introductionyear():
    data = pd.read_csv('../model/prototype/data/yearOfTechnologyIntroduction.csv',
                       header=None)

    year_of_introduction = {}

    for name, group in data.groupby(0):
        group = group.copy()
        try:
            assettype = AssetTypes[name.upper()]
        except KeyError:
            pass
        else:
            group.loc[:, 1] = group.loc[:, 1].apply(str.upper)
            data = group.loc[:, 1:].set_index(1)
            year_of_introduction[assettype.name] = data

    return year_of_introduction


class SynethicFuelLocationsEnum(enum.Enum):
    MAASVLAKTE = 'D34'
    BOTLEK = 'D35'

paths = generate_enums()
if __name__ == '__main__':
    jvm = "/usr/lib/jvm/java-8-openjdk-amd64"
    if not os.path.exists(jvm):
        jvm = None

    ema_logging.log_to_stderr(ema_logging.INFO)

    assets = get_assets()

    model = WindMasterModel("windmaster", wd='../model/prototype',
                                model_file='windmaster.nlogo',
                                jvm_home=jvm,
                                #netlogo_home="/usr/bin/NetLogo 6.0.4/",
                                #netlogo_version="6.0"
                                )

    with open('delta_dicts_list_rep_id.json') as f:
        delta_dicts_list = json.load(f)

    model.replications = delta_dicts_list
    model.nticks = 30

    model.assets = assets
    model.yearofintroduction = get_introductionyear()
    model.paths = paths

    uncertainties = []
    for assettype, paths in paths.items():
        if assettype != "SMR":
            unc = CategoricalParameter(f"{assettype} paths", paths)
            uncertainties.append(unc)

    uncertainties += [IntegerParameter("timing CCS", 2022, 2030),
                      BooleanParameter("offshore wind growth"),
                      CategoricalParameter("decisionMakingModel",
                                           ["Reactive", "Current",
                                            "Proactive", "Collaborative"]),
                      RealParameter("capex_factor", 0.7, 1.3),
                      RealParameter("leadtime_factor", 0.7, 1.3),
                      BooleanParameter("shuffle-needed-investments?"),
                      IntegerParameter("random-seed", -2147483648, 2147483647)
                      ]

    model.uncertainties = uncertainties

    outcomes =       [ArrayOutcome('stedin_capacity'),
                      ArrayOutcome('stedin_load'),
                      ArrayOutcome('tennet_capacity'),
                      ArrayOutcome('tennet_load'),
                      ArrayOutcome('gasunie_capacity'),
                      ArrayOutcome('stedin capex'),
                      ArrayOutcome('tennet capex'),
                      ArrayOutcome('gasunie capex'),
                      ArrayOutcome('collaborative capex'),
                      ArrayOutcome('h2_import'),
                      ArrayOutcome('stedin_lost'),
                      ArrayOutcome('first_failure'),
                      ArrayOutcome('missed_over_time')
                      ]
    for tick in range (0, model.nticks):
        outcomes += [ArrayOutcome(f'investments_tick_{tick}')]

    model.outcomes = outcomes

    _logger.info(f"{len(uncertainties)} uncertainties defined")
    _logger.info(f"{len(model.replications)} replications defined")


    n_scenarios = 1
    # print(datetime.datetime.now())
   # with SequentialEvaluator(model) as evaluator:
   #  with MultiprocessingEvaluator(model, n_processes=4) as evaluator:
   # #      results = evaluator.perform_experiments(n_scenarios, uncertainty_sampling=SOBOL)
   #
   #  save_results(results, f'./results/{n_scenarios}_scenarios_{len(model.replications)} replications_SOBOL.tar.gz')
   #  print(datetime.datetime.now())

    # os.system('git add --all')
    # os.system('git commit -m "add results"')
    # os.system('git push')
    # os.system('sudo poweroff')
