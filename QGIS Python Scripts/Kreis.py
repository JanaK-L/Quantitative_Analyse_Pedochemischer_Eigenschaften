# Imports: alles was man benutzt, muss man auch einfügen!!!
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFile,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterBoolean)
from qgis import processing
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from pysptools import spectro
from scipy.integrate import trapz

# Unsere neu erstellte Klasse QuantiProcessingAlgorithm erbt von der Klasse
# QgsProcessingAlgorithm. Dies ist in QGIS so erwünscht.
class QuantiKreisProcessingAlgorithm(QgsProcessingAlgorithm):

    # Klassenvariablen:
    # Zwei Konstanten, welche für die Parameterübergabe benutzt werden, wenn
    # man z.B. das Script von der Konsole oder von einem anderen Algorithmus
    # aufrufen würde.
    INPUT = 'INPUT'
    INPUT_ONE = "INPUT_ONE"
    INPUT_TWO = "INPUT_TWO"
    INPUT_KREIS = "INPUT_KREIS"
    INPUT_FLÄCHE = "INPUT_FLÄCHE"
    INPUT_STEIGUNG = "INPUT_STEIGUNG"

    # Methoden:
    # Die Klasse muss über folgende 5 Methoden verfügen:
    # createInstance, name, displayName, initAlgorithm, processAlgorithm

    # Erstellung und Rückgabe einer Instanz der Klasse mit Hilfe des
    # Konstruktoraufrufs.
    def createInstance(self):
        return QuantiKreisProcessingAlgorithm()

    # Gibt den Identifikationsnamen des Algorithmus zurück. Der Name sollte
    # einzigartig innerhalb eines jeden Providers sein und nur aus
    # Kleinbuchstaben bestehen (keine Leerzeichen oder sonstiger Shit).
    def name(self):
        return 'kreis'

    # Gibt den Anzeigenamen des Algorithmus zurück, der vom User gesehen wird.
    # Der Anzeigename muss zuvor übersetzt werden (translated, siehe tr() Methode).
    def displayName(self):
        return self.tr('Kreis')

    # In dieser Methode werden Ein- und Ausgabeparameter definiert und
    # insbesondere welche Eigenschaften diese haben müssen.
    def initAlgorithm(self, config=None):

        # Input soll der Ordner mit den hyperspektralen Daten sein.
        # Auf Klasse des Parameters und die Klassenattribute achten.
        # QgsProcessingParameterFile hat als Attribute Folder oder File.
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                self.tr('Input Ordner mit den txt Dateien, die mit dem Skript \"Spektren als Graphen\" erzeugt wurde.'),
                QgsProcessingParameterFile.Folder
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_ONE,
                self.tr('Anfang des Wellenlängenbereichs eingeben.'),
                QgsProcessingParameterNumber.Double,
                0.85
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.INPUT_TWO,
                self.tr('Ende des Wellenlängenbereichs eingeben.'),
                QgsProcessingParameterNumber.Double,
                0.95
            )
        )

        # Input, Boolean, wenn true, dann sollen Berechnungen nochmal gemacht werden
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_KREIS,
                self.tr('Kreis auf dem CR in angegebenem Bereich berechnen?'),
                False
            )
        )

        # Input, Boolean, wenn true, dann sollen Berechnungen nochmal gemacht werden
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_FLÄCHE,
                self.tr('Flächeninhalt unterhalb des normalen Spektrums berechnen?'),
                False
            )
        )

        # Input, Boolean, wenn true, dann sollen Berechnungen nochmal gemacht werden
        self.addParameter(
            QgsProcessingParameterBoolean(
                self.INPUT_STEIGUNG,
                self.tr('Steigung und Wassergehalt von 0.5 bis 0.64?'),
                False
            )
        )

    # In dieser Methode wird festgelegt, was der eigentliche Algorithmus tut.
    def processAlgorithm(self, parameters, context, feedback):
        # Den ersten Parameter (Ordnerpfad) als String holen.
        # print(self.parameterAsFile(parameters, "INPUT", context))
        quellordnerpfad = self.parameterAsFile(parameters, "INPUT", context)
        kreis = self.parameterAsBool(parameters, "INPUT_KREIS", context)
        fläche = self.parameterAsBool(parameters, "INPUT_FLÄCHE", context)
        steigung = self.parameterAsBool(parameters, "INPUT_STEIGUNG", context)

        # Wellenlängenbereich als zwei float inputs nehmen
        # wellenlängenbereich = [0.85,0.95] #hier können die Werte verändert werden
        wellenlängenbereich = [self.parameterAsDouble(parameters, "INPUT_ONE", context), self.parameterAsDouble(parameters, "INPUT_TWO", context)]

        # Grad des Polygons festlegen
        gradDesPolynoms = 4

        # print(os.getcwd()) # zum überprüfen, ob man bei relativen Pfaden im richtigen Working Directory ist
        # war natürlich im falschen directory, also workingDirectory ändern
        os.chdir(quellordnerpfad)

        # Einen Iterator auf dem Quellordner erstellen
        obj = os.scandir(quellordnerpfad)

        # Graphen in extra Ordner speichern
        dirName = "Kreis"
        if not os.path.exists(dirName):
            os.mkdir(dirName)
            print("Das Verzeichnis " , dirName , " wurde erstellt.")
        elif os.path.exists('Kreis' + os.sep + "radien" + str(wellenlängenbereich[0]) + "_" + str(wellenlängenbereich[1]) + ".txt") and kreis:
            # falls eine datei mit dem wellenlängenbereich bereits existiert, wird sie gelöscht
            os.remove('Kreis' + os.sep + "radien" + str(wellenlängenbereich[0]) + "_" + str(wellenlängenbereich[1]) + ".txt")

        # Prüfen ob Unterordner bereits existieren, falls nicht erstellen
        dirName = "Kreis" + os.sep + "Graphen" + str(wellenlängenbereich[0]) + "_" + str(wellenlängenbereich[1])
        if not os.path.exists(dirName):
            os.mkdir(dirName)
            print("Das Verzeichnis " , dirName , " wurde erstellt.")

        # ----------------------------------------------------------------------------------
        # Graphen in extra Ordner speichern
        dirName = "Flaeche"
        if not os.path.exists(dirName):
            os.mkdir(dirName)
            print("Das Verzeichnis " , dirName , " wurde erstellt.")
        elif os.path.exists('Flaeche' + os.sep + "flaecheUnterGraph" + ".txt") and fläche:
            # falls eine datei mit dem wellenlängenbereich bereits existiert, wird sie gelöscht
            os.remove('Flaeche' + os.sep + "flaecheUnterGraph" + ".txt")


        # ----------------------------------------------------------------------------------
        # Graphen in extra Ordner speichern
        dirName = "Steigung"
        if not os.path.exists(dirName):
            os.mkdir(dirName)
            print("Das Verzeichnis " , dirName , " wurde erstellt.")
        elif os.path.exists('Steigung' + os.sep + "SteigungVon0.5bis0.64" + ".txt") and steigung:
            # falls eine datei mit dem wellenlängenbereich bereits existiert, wird sie gelöscht
            os.remove('Steigung' + os.sep + "SteigungVon0.5bis0.64" + ".txt")

        # Grad des Polygons festlegen
        gradDesPolynoms = 4


        # Über alle Dateien im Ordner iterieren
        for file in obj:
            if file.is_dir():
                print(file.name + " ist ein Verzeichnis, in welches ich nicht hineinschauen will.")
            elif file.is_file() and file.name.endswith(".rfc"):
                # eine Datei zum lesen (r = read) öffnen
                spektrum = open(file.name, "r")

                # Anzahl Zeilen des Datensatzes bestimmen (wird später benötigt beim Erstellen des leeren Numpy Arrays)
                anzahlZeilen = 0
                for zeile in spektrum:
                    if not zeile[0] == "!" and not zeile[0] == '"' and not zeile[0] == "#":
                        anzahlZeilen += 1

                # geöffnete Datei wieder schließen, um Ressourcen zu sparen
                spektrum.close()

                # Graph Array der Größe anzahlZeilen X zwei erstellen und mit Nullen initialisieren
                graph = np.zeros([anzahlZeilen,2], dtype=float)
                # Array mit Werten füllen, dafür muss die Datei wieder geöffnet werden
                spektrum = open(file.name, "r")
                Wert = ""
                counter = -1
                for zeile in spektrum: # sicherstellen, dass die Zeile mit einer Zahl beginnt
                    if not zeile[0] == "!" and not zeile[0] == '"' and not zeile[0] == "#":
                        counter += 1
                        for i in zeile:
                            if i != " ":
                                Wert += i
                            else:
                                if Wert != "":
                                    graph[counter,0] = Wert
                                    Wert = ""
                        graph[counter,1] = Wert
                        Wert = ""

                # geöffnete Datei wieder schließen, um Ressourcen zu sparen
                spektrum.close()


                # --------------------------------------------------------------------------------
                # Continuum Removal bestimmen
                # Index Werte bestimmen, liefert nur die y Werte als 1D Array, x Werte weiterhin aus dem graph array nehmen
                # als parameter zuerst pixel, dann die wellenlänge, je als 1D arrays
                werteHülle = spectro.convex_hull_removal(graph[:,1],graph[:,0])


                # --------------------------------------------------------------------------------
                # Polynom eines bestimmten Grades für einen bestimmten Bereich berechnen
                if kreis:
                    Absorptionsbande = []
                    AbsorptionsbandeOriginal = []
                    WellenlängenAbsorption = []
                    nummer = 0
                    nummern = []

                    # x Werte im Originalgraph durchlaufen
                    for i in graph[:,0]:
                        if i >= wellenlängenbereich[0] and i <= wellenlängenbereich[1]:
                            nummern.append(nummer)
                            WellenlängenAbsorption.append(i)
                        nummer += 1

                    for i in nummern:
                        Absorptionsbande.append(werteHülle[0][i])

                    # Absorptionsbande Originalgraph
                    for i in nummern:
                        AbsorptionsbandeOriginal.append(graph[i,1])

                    # Polygon finden, was das ganze annähert
                    poly_fit = np.poly1d(np.polyfit(WellenlängenAbsorption,Absorptionsbande, gradDesPolynoms))

                    #Origanlspektrum:
                    poly_fit_original = np.poly1d(np.polyfit(WellenlängenAbsorption,AbsorptionsbandeOriginal, gradDesPolynoms))
                    #print(poly_fit)
                    #print(poly_fit_original)

                    # damit x achse richtig skaliert wird
                    xx = np.linspace(wellenlängenbereich[0], wellenlängenbereich[1], 1000)

                    #Tiefpunktberechnung/Kreisberechnung/whatever auf dem Polynom im bestimmten Wellenlängenbereich!
                    minimumY = poly_fit(wellenlängenbereich[0])
                    minimumX = wellenlängenbereich[0]

                    # Breite und Tiefe
                    breite = (minimumY - poly_fit_original(minimumX)) / minimumY
                    tiefe = 1 - minimumY


                    # y minimum suchen, da dort der tiefpunkt ist
                    for i in WellenlängenAbsorption:
                        if poly_fit(i) <= minimumY:
                            minimumY = poly_fit(i)
                            minimumX = i

                    punkt = (minimumX, minimumY)

                    # erste Ableitung
                    ersteAbleitung = poly_fit.deriv()

                    # zweite Ableitungen bestimmen
                    zweiteAbleitung = ersteAbleitung.deriv()

                    # Radius bestimmen
                    radius = ((1 + ersteAbleitung(minimumX)**2)**1.5)/abs(zweiteAbleitung(minimumX))

                    # Mittelpunkt bestimment
                    mittelpunkt = (minimumX, minimumY+radius)

                    # Kreis berechnen
                    fig, ax = plt.subplots()
                    ax.add_patch(plt.Circle(mittelpunkt, radius, fill = False))

                    plt.title('Polynom ' + str(gradDesPolynoms) + '. Grades im Bereich von ' + str(wellenlängenbereich[0]) + ' bis ' + str(wellenlängenbereich[1]) + '\n', fontsize=15, color='black')
                    plt.xlabel('Wellenlänge')
                    plt.ylabel('Index')
                    plt.plot(xx, poly_fit(xx))
                    plt.scatter(minimumX,minimumY+radius, color="red")

                    # Ergebnisse speichern
                    # Trennzeichen des OS herausfinden mit os.sep und dann den Graphen in dem erstellten Unterordner als png speichern
                    plt.savefig('Kreis' + os.sep + "Graphen" + str(wellenlängenbereich[0]) + "_" + str(wellenlängenbereich[1]) + os.sep + file.name.replace(".rfc", "") + '.png')
                    plt.close()

                    # neue txt Datei erstellen und Daten hinten dran hängen, a = append
                    # falls die Datei noch nicht existiert, wird ein eneue Datei angelegt
                    f = open('Kreis' + os.sep + "radien" + str(wellenlängenbereich[0]) + "_" + str(wellenlängenbereich[1]) + ".txt", "a")
                    # name und Radius in eine Datei schreiben
                    f.write(file.name.replace(".rfc", "") + (";") + str(radius) + ";" + str(tiefe) + ";" + str(breite) + "\n")
                    f.close() # Datei wieder schließen


                # ----------------------------------------------------------------------------------------------
                # Flächeninhalt im normalen Graphen Array bestimmen, Achtung nur bis 2,4 als x Wert laufen
                if fläche:
                    AbsorptionsbandeOriginal = []
                    WellenlängenAbsorption = []
                    nummer = 0
                    nummern = []
                    wellenlängenbereich_ALL = [0.4, 2.4]
                    # x Werte im Originalgraph durchlaufen
                    for i in graph[:,0]:
                        if i >= wellenlängenbereich_ALL[0] and i <= wellenlängenbereich_ALL[1]:
                            nummern.append(nummer)
                            WellenlängenAbsorption.append(i)
                        nummer += 1

                    # Absorptionsbande Originalgraph
                    for i in nummern:
                        AbsorptionsbandeOriginal.append(graph[i,1])

                    gesamteFunktion = np.poly1d(np.polyfit(WellenlängenAbsorption, AbsorptionsbandeOriginal, gradDesPolynoms))
                    flächeUnterDemGraphen = '{:18.16f}'.format(trapz(gesamteFunktion))

                    # neue txt Datei erstellen und Daten hinten dran hängen, a = append
                    # falls die Datei noch nicht existiert, wird ein eneue Datei angelegt
                    f = open('Flaeche' + os.sep + "flaecheUnterGraph" + ".txt", "a")
                    # name und Radius in eine Datei schreiben
                    f.write(file.name.replace(".rfc", "") + (";") + str(flächeUnterDemGraphen) + "\n")
                    f.close() # Datei wieder schließen

                # ----------------------------------------------------------------------------------------------
                # Steigung von 0.5 zu 0.64 Mikrometer bestimmen. antiproportional zum Eisengehalt
                if steigung:
                    AbsorptionsbandeOriginal = []
                    WellenlängenAbsorption = []
                    nummer = 0
                    nummern = []
                    wellenlängenbereich_ALL = [0.4, 2.4]

                    # x Werte im Originalgraph durchlaufen
                    for i in graph[:,0]:
                        if i >= wellenlängenbereich_ALL[0] and i <= wellenlängenbereich_ALL[1]:
                            nummern.append(nummer)
                            WellenlängenAbsorption.append(i)
                        nummer += 1

                    # Absorptionsbande Originalgraph
                    for i in nummern:
                        AbsorptionsbandeOriginal.append(graph[i,1])

                    #Origanlspektrum:
                    poly_fit_original = np.poly1d(np.polyfit(WellenlängenAbsorption,AbsorptionsbandeOriginal, gradDesPolynoms))

                    dx = 0.14
                    dy = poly_fit_original(0.64) - poly_fit_original(0.5)

                    Steigung1 = dx/dy

                    #wenig Wassergehalt
                    dx = 0.042
                    dy = poly_fit_original(0.596) - poly_fit_original(0.554)

                    Steigung2 = dx/dy

                    #viel Wassergehalt
                    dx = 0.04
                    dy = poly_fit_original(0.54) - poly_fit_original(0.5)

                    Steigung3 = dx/dy

                    if abs(Steigung3) > abs(Steigung2):
                        wassergehalt = "Eisen mit viel Wassergehalt"
                    else:
                        wassergehalt = "Eisen mit wenig Wassergehalt"


                    # neue txt Datei erstellen und Daten hinten dran hängen, a = append
                    # falls die Datei noch nicht existiert, wird ein eneue Datei angelegt
                    f = open('Steigung' + os.sep + "SteigungVon0.5bis0.64" + ".txt", "a")
                    # name und Radius in eine Datei schreiben
                    f.write(file.name.replace(".rfc", "") + ";" + str(Steigung1) + "\n")
                    f.close() # Datei wieder schließen


        # Es muss eine Map mit Ergebnissen zurückgegeben werden (Ergebnisse
        # können statistische Werte oder Layer oder sonstiges sein).
        return {'OUTPUT': 1}


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
        return self.tr("Dieses Skript berechnet die Radien von Krümmungskreisen auf "
        + " den Tiefpunkten von angenäherten Polynomen vierten Grades, schreibt die Radien in eine txt Datei und speichert die Graphen mit den Krümmungskreisen als Bilder ab."
        + "")
