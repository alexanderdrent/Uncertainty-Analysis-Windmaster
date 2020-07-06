'''
Created on 1 Apr 2019

@author: jhkwakkel
'''
import pandas as pd

investments = pd.read_csv('./data/investIDwindmaster.csv')
investment_set = set(investments.iloc[:,0])

all_assets = pd.read_csv("./data/conversionAssets.csv",
                     header=17, usecols=["Conversion asset ID [string] – Must be unique",
                                         "assetTypes", 
                                         "Asset description –  human readable form – [String]"])

descr = all_assets.iloc[:,1]

print(set(descr).intersection(investment_set))