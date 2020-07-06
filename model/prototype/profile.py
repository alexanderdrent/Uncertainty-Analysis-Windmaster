'''
Created on 30 Mar 2019

@author: jhkwakkel
'''
import collections
import functools
import time

import pandas as pd

__all__ = ['profile']


class Profile(object):
    
    def __init__(self):
        self.ncalls = collections.defaultdict(int)
        pass
    
    def __call__(self, func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            
            self.ncalls[func] += 1

            starttime = time.time()
            value = func(*args, **kwargs)
            endtime = time.time()
            
            delta = endtime-starttime
            
            # write to 
            self.write(func, starttime, endtime, delta, self.ncalls[func])
            
            return value
        return wrapper
    
    def write(self, func, starttime, endtime, totaltime, ncals):
        print(f"{func.__name__} {starttime} {endtime} {totaltime} {ncals}")


profile = Profile()
profile = Profile()