# -*- coding: utf-8 -*-
'''
/***************************************************************************
 OfflineMapMatching
                                 A QGIS plugin
a QGIS-plugin for matching a trajectory with a network using a Hidden Markov Model and Viterbi algorithm
Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2018-06-14
        git sha              : $Format:%H$
        copyright            : (C) 2018 by Christoph Jung
        email                : jagodki.cj@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
'''
from PyQt5.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt5.QtGui import QIcon, QTextCursor
from PyQt5.QtWidgets import QAction, QMenu
from qgis.gui import QgsMessageBar
from qgis.core import *
import time, traceback, sys, inspect, processing

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .offline_map_matching_dialog import OfflineMapMatchingDialog
import os.path

#import own classes
from .mm.map_matcher import *
from .mm_processing.offline_map_matching_provider import *
'''
cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]

if cmd_folder not in sys.path:
    sys.path.insert(0, cmd_folder)
'''
class OfflineMapMatching:
    '''QGIS Plugin Implementation.'''

    def __init__(self, iface):
        '''Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        '''
        
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OfflineMapMatching_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = OfflineMapMatchingDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Offline-MapMatching')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'OfflineMapMatching')
        self.toolbar.setObjectName(u'OfflineMapMatching')
        
        #add help-document to the GUI
        dir = os.path.dirname(__file__)
        file = os.path.abspath(os.path.join(dir, 'help_docs', 'help.html'))
        if os.path.exists(file):
            with open(file) as helpf:
                help = helpf.read()
                self.dlg.textBrowser_help.insertHtml(help)
                self.dlg.textBrowser_help.moveCursor(QTextCursor.Start)
        
        #declare additional instance vars
        self.map_matcher = MapMatcher()
        self.provider = OfflineMapMatchingProvider()
        
        #connect slots and signals
        self.dlg.comboBox_trajectory.currentIndexChanged.connect(self.startPopulateFieldsComboBox)
        self.dlg.pushButton_start.clicked.connect(self.startMapMatching)
        
        #set a default crs to avoid problems in QGIS 3.4
        self.dlg.mQgsProjectionSelectionWidget.setCrs(QgsCoordinateReferenceSystem('EPSG:4326'))

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        '''Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        '''
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OfflineMapMatching', message)


    def add_action(
        self,
        icon_path,
        text,
        callback=None,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        action=None):
        '''Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        '''

        icon = QIcon(icon_path)
        if action is None:
            action = QAction(icon, text, parent)
            action.triggered.connect(callback)
            action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

#        self.iface.vectorMenu().addAction(action)
        
        self.actions.append(action)

        return action

    def initGui(self):
        '''Create the menu entries, toolbar icons inside the QGIS GUI and add a new processing provider.'''
        icon_path = ':/plugins/offline_map_matching/icons/icon.png'
        
        #set up entries for the gui
        self.add_action(
            icon_path,
            text=self.tr(u'Match Trajectory'),
            callback=self.matchTrajectory,
            parent=self.iface.mainWindow())
        
        #init the preprocessing group with their entries
        menu = QMenu()
        
        #add icons
        icon_clip = QIcon(':/plugins/offline_map_matching/icons/clipping_icon.png')
        icon_density = QIcon(':/plugins/offline_map_matching/icons/reduce_density_icon.png')
        icon_pp = QIcon(':/plugins/offline_map_matching/icons/preprocessing_icon.png')
        
        #add actions
        action_clip = menu.addAction(icon_clip, 'Clip Network', self.clipNetwork)
        action_clip.setObjectName('clip_network')
        
        action_reduce = menu.addAction(icon_density, 'Reduce Trajectory Density', self.reduceDensity)
        action_reduce.setObjectName('reduce_density')
        
        #add main entry
        preprocessing_action = QAction(icon_pp, 'Preprocessing', self.iface.mainWindow())
        preprocessing_action.setMenu(menu)
        self.add_action(
            '',
            text=self.tr(u'Preprocessing'),
            action=preprocessing_action,
            parent=self.iface.mainWindow(),
            add_to_toolbar=False)
        
#        preprocessing_action.setMenu(menu)
#        self.actions.append(preprocessing_action)
#        self.iface.addPluginToVectorMenu(self.menu, preprocessing_action)
        
        #add the processing provider
        QgsApplication.processingRegistry().addProvider(self.provider)

    
    def clipNetwork(self):
        processing.execAlgorithmDialog('omm:clip_network', {})
    
    def reduceDensity(self):
        processing.execAlgorithmDialog('omm:reduce_trajectory_density', {})
        
    def fastTrajectoryMatching(self):
        processing.execAlgorithmDialog('omm:fast_trajectory_matching', {})
    
    def matchTrajectory(self):
        processing.execAlgorithmDialog('omm:match_trajectory', {})
    
    def unload(self):
        '''Removes the plugin menu item and icon from QGIS GUI. Remove the processing provider.'''
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&Offline-MapMatching'),
                action)
            #self.iface.vectorMenu().removeAction(action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar
        
        #remove the processing provider
        QgsApplication.processingRegistry().removeProvider(self.provider)


    def run(self):
        '''Run method that performs all the real work'''
        #populate the comboboxes with the available layers
        self.populateComboBox('network')
        self.populateComboBox('trajectory')
        self.populateComboBox('fields')
        
        #clear all other gui elements
        self.dlg.progressBar.setValue(0)
        self.dlg.doubleSpinBox_sigma.setValue(50.0)
        self.dlg.doubleSpinBox_my.setValue(0.0)
        self.dlg.doubleSpinBox_beta.setValue(30.0)
        self.dlg.doubleSpinBox_max.setValue(0.0)
        self.dlg.label_info.setText('')
        #self.dlg.lineEdit_crs.setText('')
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        #result = self.dlg.exec_()
        # See if OK was pressed
        #if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            #pass
    
    def populateComboBox(self, type):
        '''Populate the given combobox.'''
        if type == 'network':
            self.map_matcher.fillLayerComboBox(self.iface, self.dlg.comboBox_network, 'LINESTRING')
        elif type == 'trajectory':
            self.map_matcher.fillLayerComboBox(self.iface, self.dlg.comboBox_trajectory, 'POINT')
        elif type == 'fields':
            self.map_matcher.fillAttributeComboBox(self.dlg.comboBox_trajectoryID, self.dlg.comboBox_trajectory.currentText())

    def startPopulateFieldsComboBox(self):
        self.populateComboBox('fields')
    
    def startMapMatching(self):
        self.dlg.groupBox_data.setEnabled(False)
        self.dlg.groupBox_settings.setEnabled(False)
        self.dlg.pushButton_start.setEnabled(False)
        
        try:
            start_time = time.time()
            result = self.map_matcher.startViterbiMatchingGui(
                          self.dlg.progressBar,
                          self.dlg.comboBox_trajectory.currentText(),
                          self.dlg.comboBox_network.currentText(),
                          self.dlg.comboBox_trajectoryID.currentText(),
                          self.dlg.doubleSpinBox_sigma.value(),
                          self.dlg.doubleSpinBox_my.value(),
                          self.dlg.doubleSpinBox_beta.value(),
                          self.dlg.doubleSpinBox_max.value(),
                          self.dlg.label_info,
                          self.dlg.mQgsProjectionSelectionWidget.crs().authid())
            
            if result == 0:
                self.iface.messageBar().pushMessage('map matching finished ^o^ - time: ' + str(round(time.time() - start_time, 2)) + ' sec', level=Qgis.Success, duration=60)
            elif result == -1:
                self.iface.messageBar().pushMessage('Error during calculation of candidates. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
            elif result == -2:
                self.iface.messageBar().pushMessage('Error during calculation of starting probabilities. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
            elif result == -3:
                self.iface.messageBar().pushMessage('Error during calculation of transition probabilities. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
            elif result == -4:
                self.iface.messageBar().pushMessage('Error during calculation of backtracking. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
            elif result == -5:
                self.iface.messageBar().pushMessage('Error during calculating the most likely path. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
            elif result == -6:
                self.iface.messageBar().pushMessage('Error during calculating the path on network. Check the QGIS-log for further information.', level=Qgis.Warning, duration=60)
    
        except:
            QgsMessageLog.logMessage(traceback.format_exc(), level=Qgis.Critical)
            self.iface.messageBar().pushMessage('An error occured. Please look into the log and/or Python console for further information.', level=Qgis.Critical, duration=60)
        
        
        self.dlg.groupBox_data.setEnabled(True)
        self.dlg.groupBox_settings.setEnabled(True)
        self.dlg.pushButton_start.setEnabled(True)