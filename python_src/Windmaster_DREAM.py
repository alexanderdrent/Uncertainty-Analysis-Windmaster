import pyNetLogo

netlogo = pyNetLogo.NetLogoLink(gui=False)
import numpy as np
import os
from pydream import core
from pydream.parameters import SampledParam
from pydream.convergence import Gelman_Rubin
from scipy.stats import uniform
import pandas as pd
import enum

init = True


def calculate_likelihood_dream_wm(parameters):
    global init
    if init:
        print("Setting up packages and Netlogo model")
        # import packages - again, required due to windows forking.
        global np
        from pydream.parameters import SampledParam
        global pyNetLogo
        import pyNetLogo
        global netlogo
        netlogo = pyNetLogo.NetLogoLink(gui=False)
        from collections import Counter
        global math
        import math
        global pd
        import pandas as pd
        global enum
        import enum
        global Counter
        global namedtuple
        from collections import namedtuple, Counter

        def init_WindMasterModel():
            netlogo.load_model('../model/prototype/windmaster.nlogo')
            for entry in ["provideWarnings?", "verbose?", "debug?"]:
                netlogo.command(f"set {entry} false")
            netlogo.command("setup")

        global get_introductionyear

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

        global yearofintroduction
        yearofintroduction = get_introductionyear()

        global create_paths

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

        global generate_enums

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

        global SynethicFuelLocationsEnum

        class SynethicFuelLocationsEnum(enum.Enum):
            MAASVLAKTE = 'D34'
            BOTLEK = 'D35'

        global paths
        paths = generate_enums()

        global get_year_of_availability

        def get_year_of_availability(assettype, technology):
            data = yearofintroduction[assettype.name]
            a = data.loc[technology.name]
            try:
                year = int(a.values[0])
            except ValueError:
                year = 2040

            return year

        global get_assets

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

        global assets
        assets = get_assets()

        global create_event

        def create_event(asset_id, assettype, technology, year, volume=-1):
            return asset_id, assettype.value, technology.value, year, volume

        global sigmoid

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

        global fixed_unc
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

        global fixed_values_unc
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
             'yearKochPhaseout': 2030.0,
             }

        global delta_dict
        delta_dict = {"C1": 4,
                      "C2": 0,
                      "C5": 4,
                      "C10": 1,
                      "C11": 1,
                      "C12": 0,
                      "C16": 0,
                      "C20": 3,
                      "C21": 4,
                      "C22": 4,
                      "C24": 1,
                      "C25": 2,
                      "C27": 3,
                      "C28": 0,
                      "C33": 2,
                      "C34": 5,
                      "C35": 5,
                      "C43": 0,
                      "C45": 0,
                      "C50": 5,
                      "C53": 4,
                      "C56": 5,
                      "C58": 3,
                      "C59": 1,
                      "C69": 1,
                      "C70": 1,
                      "C71": 4,
                      "C7": 4,
                      "C8": 0,
                      "C9": 1,
                      "C17": 0,
                      "C18": 1,
                      "C19": 5,
                      "C26": 4,
                      "C39": 0,
                      "C41": 5,
                      "C42": 3,
                      "C47": 1,
                      "C51": 3,
                      "C54": 5,
                      "C55": 2,
                      "C57": 2,
                      "C72": 5,
                      "C73": 1,
                      "C74": 3,
                      "C4": 5,
                      "C14": 0,
                      "C15": 1,
                      "C23": 2,
                      "C29": 1,
                      "C30": 1,
                      "C36": 5,
                      "C37": 0,
                      "C44": 1,
                      "C52": 5,
                      "C63": 3,
                      "C64": 0,
                      "C31": 1,
                      "C32": 3,
                      "C48": 1,
                      "C49": 4,
                      "C62": 1,
                      "C40 delta": 1,
                      "C66 delta": 0,
                      "C67 delta": 3,
                      "C68 delta": 4,
                      "C13 delta": 0,
                      "C60 delta": 1,
                      "C61 delta": 2
                      }

        global WindMasterModel

        def WindMasterModel(parameters):
            experiment = {pname: pvalue for pname, pvalue in zip(vars, parameters)}
            nticks = 30
            random_seed = 1
            start_h2import = 2025
            for unc in fixed_unc:
                experiment[unc] = fixed_values_unc[unc]
                if unc == "SMR paths":
                    experiment[unc] = eval(fixed_values_unc[unc])
            experiment.update(delta_dict)

            netlogo.command("startNewRun")

            yearofintroduction['SMR'].loc["ELECTROLYSIS_H2O"] = experiment["year of introduction ELECTROLYSIS_H20"]
            yearofintroduction['SMR'].loc["SMR_CCS"] = int(np.floor(experiment["timing CCS"]))

            netlogo.command('random-seed {}'.format(random_seed))
            dm = ["Reactive", "Current", "Proactive", "Collaborative"][int(np.floor(experiment["decisionMakingModel"]))]
            netlogo.command(f"set decisionMakingModel \"{dm}\"")
            netlogo.command("ask infraProviders [set leadtime_factor {}]".format(experiment["leadtime_factor"]))

            start_h2production = get_year_of_availability(AssetTypes.SMR,
                                                          experiment[f"{AssetTypes.SMR.name} paths"].value[
                                                              0])
            year_h2 = min(start_h2import, start_h2production)

            for value in yearofintroduction.values():
                for item in ["HYBRIDH2", "H2"]:
                    try:
                        value.loc[item] = year_h2
                    except ValueError:
                        pass

            events = []
            paths = generate_enums()
            for assettype, paths in paths.items():
                if assettype != "SMR":
                    experiment[f"{assettype} paths"] = list(paths)[int(np.floor(experiment[f"{assettype} paths"]))]

            # assettypes with pathways
            paths = generate_enums()
            for assettype in paths.keys():
                assettype = AssetTypes[assettype]
                try:
                    path = experiment[f"{assettype.name} paths"]
                except KeyError:
                    # print(f"{assettype.name} path not defined")
                    continue

                for asset_id in assets[assettype.name]:
                    delta = experiment[asset_id]

                    for bt in path.value:
                        year_of_availability = get_year_of_availability(assettype, bt)
                        year = year_of_availability + delta
                        event = create_event(asset_id, assettype, bt, year)
                        events.append(event)

                if assettype.name == "SMR":
                    location = experiment["location h2 production"]

                    if location == 'maasvlakte':
                        if len(path.value) == 1:
                            year = get_year_of_availability(assettype, bt)
                            event = create_event('C76', assettype, path.value[0],
                                                 year)
                            events.append(event)
                        else:
                            for bt, asset_id in zip(path.value, ['C75', 'C76']):
                                year = get_year_of_availability(assettype, bt)
                                event = create_event(asset_id, assettype, bt, year)
                                events.append(event)
                    elif location == 'botlek':
                        if len(path.value) == 1:
                            year = get_year_of_availability(assettype, bt)
                            event = create_event('C79', assettype, path.value[0],
                                                 year)
                            events.append(event)
                        else:
                            for bt, asset_id in zip(path.value, ['C78', 'C79']):
                                year = get_year_of_availability(assettype, bt)
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
            for assetid in assets[assettype.name]:
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
                for assetid in assets[assettype.name]:
                    delta = experiment[f"{assetid} delta"]
                    year = start_h2production + delta

                    event = create_event(assetid, assettype, FakeTechnology(0),
                                         year)
                    events.append(event)

            # offshore wind scenarios
            offshore_wind = experiment["offshore wind growth"]

            if offshore_wind > 0.5:
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

            netlogo.command(f"set scenario {eventstring}")
            netlogo.command("set yearGunvorPhaseout {}".format(experiment["yearGunvorPhaseout"]))
            netlogo.command("set yearKochPhaseout {}".format(experiment["yearKochPhaseout"]))

            bp = experiment["yearHydrocrackerBP"]
            if bp:
                netlogo.command("set yearHydrocrackerBP 2025")
            else:
                netlogo.command("set yearBPOffline {}".format(experiment["yearBPOffline"]))

            try:
                netlogo.command(f"repeat {nticks}  [go]")
            except Exception as e:
                raise CaseError(repr(e), experiment)

            capex = netlogo.report('capexOverTime')

            scenario_execution = netlogo.report('reportRealisedScenarioEvents')
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

            stedin_capex = sum([entry[0] for entry in capex])
            tennet_capex = sum([entry[1] for entry in capex])
            gasunie_capex = sum([entry[2] for entry in capex])
            collaborative_capex = sum([entry[3] for entry in capex])
            missed_over_time = sum(missed_per_year)

            results = {"stedin capex": sum([entry[0] for entry in capex]),
                       "tennet capex": sum([entry[1] for entry in capex]),
                       "gasunie capex": sum([entry[2] for entry in capex]),
                       "collaborative capex": sum([entry[3] for entry in capex]),
                       "missed_over_time": sum(missed_per_year)
                       }

            print(results)
            return missed_over_time

        init_WindMasterModel()
        init = False
    missed_over_time = WindMasterModel(parameters)

    if missed_over_time > 150:
        distance = 1
    else:
        distance = missed_over_time - 150
    print(distance)
    return distance


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


paths = generate_enums()

vars = []

vars = ["decisionMakingModel",
        "timing CCS",
        "offshore wind growth",
        "BOILER paths",
        "FURNACE paths",
        "COGEN paths",
        "leadtime_factor"]

bounds = np.asarray([[0, 4],
                     [2022, 2031],
                     [0, 1],
                     [0, 5],
                     [0, 5],
                     [0, 4],
                     [0.6, 1.4]])
lower_bounds = bounds[:, 0]
upper_bounds = bounds[:, 1] - bounds[:, 0]

parameters_to_sample = SampledParam(uniform, loc=lower_bounds, scale=upper_bounds)

# Parameters for run_dream
n_iterations = 500
nchains = 3

if __name__ == '__main__':
    total_iterations = n_iterations
    converged=False
    sampled_params, log_ps = core.run_dream(parameters_to_sample,
                                            calculate_likelihood_dream_wm,
                                            niterations=n_iterations,
                                            nchains=nchains,
                                            random_start=True,
                                            start=None,
                                            save_history=True,
                                            adapt_gamma=False,
                                            gamma_levels=1,
                                            tempering=False,
                                            multitry=False,
                                            parallel=False,
                                            model_name='wm_model')

    # Save sampling output (sampled parameter values and their corresponding logps).
    for chain in range(len(sampled_params)):
        np.save('wm_model_sampled_params_chain_' + str(chain) + '_' + str(total_iterations), sampled_params[chain])
        np.save('wm_model_logps_chain_' + str(chain) + '_' + str(total_iterations), log_ps[chain])

    # Check convergence and continue sampling if not converged

    GR = Gelman_Rubin(sampled_params)
    print('At iteration: ', total_iterations, ' GR = ', GR)
    np.savetxt('wm_model_GelmanRubin_iteration_' + str(total_iterations) + '.txt', GR)

    old_samples = sampled_params
    if np.any(GR > 1.2):
        starts = starts = [sampled_params[chain][-1, :] for chain in range(nchains)]
        while not converged:
            total_iterations += n_iterations
            sampled_params, log_ps = core.run_dream(parameters_to_sample, calculate_likelihood_dream_wm,
                                                    niterations=n_iterations,
                                                    nchains=nchains, start=starts,
                                                    save_history=True,
                                                    adapt_gamma=False, gamma_levels=1, tempering=False,
                                                    multitry=False,
                                                    verbose=True, restart=True,
                                                    parallel=False, model_name='wm_model')

            # Save sampling output (sampled parameter values and their corresponding logps).
            for chain in range(len(sampled_params)):
                np.save('wm_model_sampled_params_chain_' + str(chain) + '_' + str(total_iterations),
                        sampled_params[chain])
                np.save('wm_model_logps_chain_' + str(chain) + '_' + str(total_iterations), log_ps[chain])

            old_samples = [np.concatenate((old_samples[chain], sampled_params[chain])) for chain in range(nchains)]
            GR = Gelman_Rubin(old_samples)
            print('At iteration: ', total_iterations, ' GR = ', GR)
            np.savetxt('wm_model_GelmanRubin_iteration_' + str(total_iterations) + '.txt', GR)

            if np.all(GR < 1.2):
                converged = True
