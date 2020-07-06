'''
Created on 27 Mar 2019

@author: jhkwakkel
'''
import windmasterTechnicalModel  # @UnresolvedImport

def test_removal_gas():

    windmasterTechnicalModel.year = 2021
    windmasterTechnicalModel.remove_gas_asset('C3')
    

def test_remove_asset():
    windmasterTechnicalModel.year = 2021
    windmasterTechnicalModel.removeAsset('C3')   
    
    windmasterTechnicalModel.update_electricity_network 
    
def test_helper1():
    windmasterTechnicalModel.helper1(windmasterTechnicalModel.electricity_grid)
    
def test_getScenario():
    windmasterTechnicalModel.getScenario()
    
def test_handle_investment():
    investment = [['TenneT150Botl_line', 'TenneT150Mersey_line'], 'TenneT',
                  21.47985272578396, 48, 2027, 0, 34, 0, 1, '150kVgrid6', 4]
    
    windmasterTechnicalModel.handle_investment(investment)


def test_get_currentinfrastructurestatus():
    windmasterTechnicalModel.getCurrentInfrastructureStatus('TenneT')

if __name__ == '__main__':
#     test_removal_gas()
#     windmasterTechnicalModel.changeAssetDemandGAS([], False)
#     test_handle_investment()
    test_get_currentinfrastructurestatus()
