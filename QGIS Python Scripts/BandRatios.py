# Imports: alles was man benutzt, muss man auch einfügen!!!
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterFolderDestination,
                       QgsRasterLayer,
                       QgsProcessingParameterBoolean)
from qgis import processing
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
import os
from qgis.core import QgsProject
from osgeo import gdal


# Unsere neu erstellte Klasse QuantiProcessingAlgorithm erbt von der Klasse
# QgsProcessingAlgorithm. Dies ist in QGIS so erwünscht.
class QuantiBandRatioProcessingAlgorithm(QgsProcessingAlgorithm):

    # Klassenvariablen:
    # Zwei Konstanten, welche für die Parameterübergabe benutzt werden, wenn
    # man z.B. das Script von der Konsole oder von einem anderen Algorithmus
    # aufrufen würde.
    INPUT = "INPUT"
    OUTPUT_BANDRATIO = "OUTPUT_BANDRATIO"
    INPUT_EISEN_EINS = "INPUT_EISEN_EINS"
    INPUT_EISEN_ZWEI = "INPUT_EISEN_ZWEI"
    INPUT_EISEN_DREI = "INPUT_EISEN_DREI"
    INPUT_EISEN_VIER = "INPUT_EISEN_VIER"
    INPUT_EISEN_FÜNF = "INPUT_EISEN_FÜNF"
    INPUT_EISEN_MULTI = "INPUT_EISEN_MULTI"
    INPUT_NDVI = "INPUT_NDVI"
    INPUT_CANORG_EINS = "INPUT_CANORG_EINS"
    INPUT_CANORG_ZWEI = "INPUT_CANORG_ZWEI"
    INPUT_CORG_EINS = "INPUT_CORG_EINS"
    INPUT_CORG_ZWEI = "INPUT_CORG_ZWEI"

    # Methoden:
    # Die Klasse muss über folgende 5 Methoden verfügen:
    # createInstance, name, displayName, initAlgorithm, processAlgorithm

    # Erstellung und Rückgabe einer Instanz der Klasse mit Hilfe des
    # Konstruktoraufrufs.
    def createInstance(self):
        return QuantiBandRatioProcessingAlgorithm()

    # Gibt den Identifikationsnamen des Algorithmus zurück. Der Name sollte
    # einzigartig innerhalb eines jeden Providers sein und nur aus
    # Kleinbuchstaben bestehen (keine Leerzeichen oder sonstiger Shit).
    def name(self):
        return 'bandratio'

    # Gibt den Anzeigenamen des Algorithmus zurück, der vom User gesehen wird.
    # Der Anzeigename muss zuvor übersetzt werden (translated, siehe tr() Methode).
    def displayName(self):
        return self.tr('Band Ratio')

    # In dieser Methode werden Ein- und Ausgabeparameter definiert und
    # insbesondere welche Eigenschaften diese haben müssen.
    def initAlgorithm(self, config=None):

        # Input soll der Ordner mit den hyperspektralen Daten sein.
        # Auf Klasse des Parameters und die Klassenattribute achten.
        # QgsProcessingParameterFile hat als Attribute Folder oder File.
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                self.tr('Input Layer mit den sechs LandsatTM Kanälen')
            )
        )

        # Input, wo soll der OutputRaster gespeichert werden
        self.addParameter(
            QgsProcessingParameterFolderDestination(
                self.OUTPUT_BANDRATIO,
                self.tr('Speicherort')
            )
        )

        # Input, Boolean, wenn true, dann soll Ratio berechnet werden
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_EINS,
                self.tr('Eisen: Band Ratio 4/3')
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_ZWEI,
                self.tr('Eisen: Band Ratio 3/1'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_DREI,
                self.tr('Eisen: Band Ratio 5/4'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_FÜNF,
                self.tr('Eisen: Band Ratio (3+5)/4'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_VIER,
                self.tr('Eisen: Summe der zwei Band Ratios 3/1 und 5/4'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_EISEN_MULTI,
                self.tr('Eisen: Layerstack (R = 3/1, G = 5/4, B = 3/1 + 5/4)'
                + "\nKann nur erstellt werden, wenn die drei dafür benötigten\nBand Ratios im gleichen Schritt bereits berechnet wurden."),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_CANORG_EINS,
                self.tr('Canorg: Band Ratio 5/7'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_CANORG_ZWEI,
                self.tr('Canorg: Band Ratio (5/7) / (4/3)'),
                False
            )
        )

        # Input Corg
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_CORG_EINS,
                self.tr('Corg: 1/(3-2)'),
                False
            )
        )

        # Input Corg
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_CORG_ZWEI,
                self.tr('Corg: ??? Work in Progress'),
                False
            )
        )

        # Input
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_NDVI,
                self.tr('NDVI'),
                False
            )
        )


    # In dieser Methode wird festgelegt, was der eigentliche Algorithmus tut.
    def processAlgorithm(self, parameters, context, feedback):
        # Inputraster holen
        raster = self.parameterAsRasterLayer(parameters, "INPUT", context)
        # Den ersten Parameter (Ordnerpfad) als String holen.
        # Entweder OUTPUT aus dem Object parameters direkt herausholen
        output = parameters['OUTPUT_BANDRATIO']
        # oder: self.parameterAsFile(parameters, "INPUT", context)

        # leere Liste von Einträgen erstellen, in welchen man alle Raster, mit denen man rechnen möchte, sammelt
        entries = []

        # Vorbereitung des QgsRasterCalculators:
        # für jedes Band (Kanal), das man verwenden will, müssen die folgenden Dinge ausgeführt werden
        rasEins = QgsRasterCalculatorEntry()
        rasEins.ref = "ras@1"
        rasEins.raster = raster
        rasEins.bandNumber = 1

        rasZwei = QgsRasterCalculatorEntry()
        rasZwei.ref = "ras@2"
        rasZwei.raster = raster
        rasZwei.bandNumber = 2

        rasDrei = QgsRasterCalculatorEntry()
        rasDrei.ref = "ras@3"
        rasDrei.raster = raster
        rasDrei.bandNumber = 3

        rasVier = QgsRasterCalculatorEntry()
        rasVier.ref = "ras@4"
        rasVier.raster = raster
        rasVier.bandNumber = 4

        rasFünf = QgsRasterCalculatorEntry()
        rasFünf.ref = "ras@5"
        rasFünf.raster = raster
        rasFünf.bandNumber = 5

        rasSechs = QgsRasterCalculatorEntry()
        rasSechs.ref = "ras@6"
        rasSechs.raster = raster
        rasSechs.bandNumber = 6

        # jeder Rasterlayer muss der Liste hinzugefügt werden
        entries.append(rasEins)
        entries.append(rasZwei)
        entries.append(rasDrei)
        entries.append(rasVier)
        entries.append(rasFünf)
        entries.append(rasSechs)

        # ----------------------------------------------------------------------------------
        # Eisen: Band Ratio 4/3
        # hebt Eisenminerale generell hervor (Hervorheben der Tiefe der Absorption im NIR)
        # Calculator: Expression, output, ...
        # ALTERNATIV das rasterio modul mit calc verwenden!
        if self.parameterAsBool(parameters, "INPUT_EISEN_EINS", context):
            outputEins = output + os.sep + "BandRatioEisen_4durch3.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("ras@4 / ras@3", outputEins, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputEins, "BandRatioEisen_4durch3")

        # ----------------------------------------------------------------------------------
        # Eisen: Band Ratio 3/1: Iron Oxide Ratio - This band ratio highlights hydrothermally altered rocks that have been subjected to oxidation of iron-bearing sulphides.
        # Rot/Blau, Hervorheben der Absorption im blauen Wellenlängenbereich
        # The ratio of bands 3/1 will enhance rocks which are rich in ferric iron oxide (limonite), for the hydrothermal alteration or the oxidation of Fe-Mg silicates.
        if self.parameterAsBool(parameters, "INPUT_EISEN_ZWEI", context):
            outputZwei = output + os.sep + "BandRatioEisen_3durch1.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("ras@3 / ras@1", outputZwei, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputZwei, "BandRatioEisen_3durch1")

        # ----------------------------------------------------------------------------------
        # Eisen: Band Ratio 5/4: Ferrous Minerals Ratio - This band ratio highlights iron-bearing minerals.
        # SWIR/NIR
        # A ratio of bands 5/4 enhances rocks which are rich in ferrous iron.
        if self.parameterAsBool(parameters, "INPUT_EISEN_DREI", context):
            outputDrei = output + os.sep + "BandRatioEisen_5durch4.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("ras@5 / ras@4", outputDrei, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputDrei, "BandRatioEisen_5durch4")

        # ----------------------------------------------------------------------------------
        # Eisen: Band Ratio 3/1 + 5/4
        if self.parameterAsBool(parameters, "INPUT_EISEN_VIER", context):
            outputVier = output + os.sep + "Eisen_Summe_3durch1_und_5durch4.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("(ras@3 / ras@1) + (ras@5 / ras@4)", outputVier, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputVier, "Eisen_Summe_3durch1_und_5durch4")

        # ----------------------------------------------------------------------------------
        # NDVI
        if self.parameterAsBool(parameters, "INPUT_NDVI", context):
            outputFünf = output + os.sep + "NDVI.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("(ras@4 - ras@3) / (ras@4 + ras@3)", outputFünf, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputFünf, "NDVI")

        # ----------------------------------------------------------------------------------
        # Eisen: Band Ratio (3+5)/4: Hervorheben der Absorption von Eisen im NIR
        if self.parameterAsBool(parameters, "INPUT_EISEN_FÜNF", context):
            outputSechs = output + os.sep + "BandRatioEisen_3plus5DURCH4.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("(ras@3 + ras@5) / ras@4", outputSechs, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputSechs, "BandRatioEisen_3plus5DURCH4")
        # ----------------------------------------------------------------------------------
        # Canorg: 5/7
        if self.parameterAsBool(parameters, "INPUT_CANORG_EINS", context):
            outputSieben = output + os.sep + "BandRatioCanorg_5durch7.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("ras@5 / ras@6", outputSieben, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputSieben, "BandRatioCanorg_5durch7")

        # ----------------------------------------------------------------------------------
        # Canorg: Band Ratio (5/7) / (4/3)
        if self.parameterAsBool(parameters, "INPUT_CANORG_ZWEI", context):
            outputAcht = output + os.sep + "BandRatioCanorg_5durch7DURCH4durch3.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("(ras@5 / ras@6) / ( ras@4 / ras@3)", outputAcht, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputAcht, "BandRatioCanorg_5durch7DURCH4durch3")

        # ----------------------------------------------------------------------------------
        # Corg: Band Ratio 1/(3-2)
        if self.parameterAsBool(parameters, "INPUT_CORG_EINS", context):
            outputNeun = output + os.sep + "BandRatioCorg_1DURCH3minus2.tif" # Speicherort festlegen
            calc = QgsRasterCalculator("ras@1 / ( ras@3 - ras@2)", outputNeun, "GTiff", raster.extent(), raster.width(),raster.height(), entries)
            calc.processCalculation() # Berechnung starten

            # Raster der Anzeige hinzufügen
            self.addToMyMap(outputNeun, "BandRatioCorg_1DURCH3minus2")

        # ----------------------------------------------------------------------------------
        # Ein Multiband Raster aus outputZwei = R und outputDrei = G und von outputZwei + outputDrei = B erstellen
        # druckt auf der python console aus, welche Parameter der Algorithmus braucht
        # processing.algorithmHelp('gdal:merge')
        if self.parameterAsBool(parameters, "INPUT_EISEN_MULTI", context) and self.parameterAsBool(parameters, "INPUT_EISEN_ZWEI", context) and self.parameterAsBool(parameters, "INPUT_EISEN_DREI", context) and self.parameterAsBool(parameters, "INPUT_EISEN_VIER", context):
            # Speicherort und Dateiname des Outputs festlegen
            multibandRasterPfad = output + os.sep + "MultibandRasterEisen.img"
            # run braucht 4 Parameter: die id des Tools, ein Dictonary mit den Parametern für das Tools
            # den context, das feedback (um den progress des Algorithmus als user verfolgen zu können)
            processing.run(
                "gdal:merge",
                {           #   Rot          Grün        Blau
                    "INPUT": [outputZwei, outputDrei, outputVier],
                    "PCR": True,
                    "SEPARATE": True,
                    "DATA_TYPE": 5,
                    "OUTPUT": multibandRasterPfad
                },
                context = context,
                feedback = feedback,
            )

            # MultiBandRaster der Anzeige hinzufügen
            self.addToMyMap(multibandRasterPfad, "MultibandRasterEisen")

        # ----------------------------------------------------------------------------------
        # Weitere Band Ratios?

        # ----------------------------------------------------------------------------------

        # Es muss eine Map mit Ergebnissen zurückgegeben werden.
        return {}

    # Methode, die den neu berechneten Layer zu der Map hinzufügt
    def addToMyMap(self, output, name):
        # Layer identifizieren, die entfernt werden sollen, da in qgis mehrere Layer den gleichen
        # Namen haben können, gibt dieser Befehl eine Liste mit allen Layern diesen Namens zurück
        rlayerList = QgsProject.instance().mapLayersByName(name)
        idListe = []

        # prüfen, ob Layer bereits in der Map vorhanden ist, falls ja, entfernen
        if len(rlayerList) != 0: # wenn die Liste nicht leer ist, dann gibt es Layer mit dem Namen
            # eine idListe erstellen
            for i in rlayerList:
                idListe.append(i.id())

            # alle Layer mit den entsprechenden IDs aus der Map entfernen
            QgsProject.instance().removeMapLayers(idListe)

        # eine RasterLayerInstanz erzeugen und der Anzeige hinzufügen
        rlayer = QgsRasterLayer(output, name)
        QgsProject.instance().addMapLayer(rlayer)

    # Methode liefert einen übersetzbaren String zurück.
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    # Gibt den Gruppennamen, zu der Gruppe, zu welcher das Script gehören soll, zurück.
    def group(self):
        return self.tr('Quanti Scripts')

    # Gibt die GruppenID als String zur Identifikation der Gruppe zurück.
    def groupId(self):
        return 'quantiscripts'

    # Kurzbeschreibung des Skripts.
    def shortHelpString(self):
        return self.tr("Auf Basis des Input Rasters werden die ausgewählten Band Ratios oder Layerstacks berechnet."
        + "Die Ergebnisse werden in dem angegebenen Ordner gespeichert und direkt der Karte hinzugefügt."
        + "\nEs wird empfohlen den NDVI nicht neu zu berechnen, da sonst die Symbology wieder verloren geht."
        + "\nEventuell muss im Anschluss die Projektion auf der Layer auf Transverse Mercator geänert werden."
        + "\nDer Constructor vom Rastercalculator ist deprecated, weshalb davor gewarnt wird, diesen zu benutzen.")
