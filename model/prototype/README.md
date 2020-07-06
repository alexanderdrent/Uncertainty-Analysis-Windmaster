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
