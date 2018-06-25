""" Commits monitoring information using gServiceInterface singleton
"""

__RCSID__ = "$Id$"

import os

from DIRAC import gLogger, gConfig, rootPath, S_OK, S_ERROR
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC.Core.Utilities import DEncode, Time
from DIRAC.ConfigurationSystem.Client import PathFinder
from DIRAC.FrameworkSystem.Client.MonitoringClient import gMonitor
from DIRAC.FrameworkSystem.private.monitoring.ServiceInterface import gServiceInterface

def initializeMonitoringHandler(serviceInfo):
  gLogger.warn(" =============== DEBUG ===============")
  return S_OK()


class MonitoringHandler(RequestHandler):
  mainName = "Framework/Monitoring"

  types_registerActivities = [dict, dict]

  def export_registerActivities(self, sourceDict, activitiesDict, componentExtraInfo={}):
    """
    Registers new activities
    """
    gLogger.info("============= sourceDict =============")
    gLogger.info(sourceDict)
    gLogger.info("=========== activitiesDict ===========")
    gLogger.info(activitiesDict)
    gLogger.info("========= componentExtraInfo =========")
    gLogger.info(componentExtraInfo)

    #return gServiceInterface.registerActivities(sourceDict, activitiesDict, componentExtraInfo)
    return S_OK(4) #Replace a sourceId
  types_commitMarks = [int, dict]

  def export_commitMarks(self, sourceId, activitiesDict, componentExtraInfo={}):
    """
    Adds marks for activities
    """
    gLogger.info("============== sourceId ==============")
    gLogger.info(sourceId)
    gLogger.info("=========== activitiesDict ===========")
    gLogger.info(activitiesDict)
    gLogger.info("========= componentExtraInfo =========")
    gLogger.info(componentExtraInfo)

    return S_OK({})

  def export_queryField(self, field, definedFields):
    """
    Returns available values for a field., given a set of fields and values,
    """
    gLogger.warn("ADD LOG FOR THAT [export_queryField]")
    return S_OK()
