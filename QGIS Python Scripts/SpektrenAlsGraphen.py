# Imports: alles was man benutzt, muss man auch einfügen!!!
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterFile)
from qgis import processing
import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull, convex_hull_plot_2d
from pysptools import spectro

# Unsere neu erstellte Klasse QuantiProcessingAlgorithm erbt von der Klasse
# QgsProcessingAlgorithm. Dies ist in QGIS so erwünscht.
class QuantiSpektrenGraphenProcessingAlgorithm(QgsProcessingAlgorithm):

    # Klassenvariablen:
    # Zwei Konstanten, welche für die Parameterübergabe benutzt werden, wenn
    # man z.B. das Script von der Konsole oder von einem anderen Algorithmus
    # aufrufen würde.
    INPUT = 'INPUT'


    # Methoden:
    # Die Klasse muss über folgende 5 Methoden verfügen:
    # createInstance, name, displayName, initAlgorithm, processAlgorithm

    # Erstellung und Rückgabe einer Instanz der Klasse mit Hilfe des
    # Konstruktoraufrufs.
    def createInstance(self):
        return QuantiSpektrenGraphenProcessingAlgorithm()

    # Gibt den Identifikationsnamen des Algorithmus zurück. Der Name sollte
    # einzigartig innerhalb eines jeden Providers sein und nur aus
    # Kleinbuchstaben bestehen (keine Leerzeichen oder sonstiger Shit).
    def name(self):
        return 'spektrenalsgraphen'

    # Gibt den Anzeigenamen des Algorithmus zurück, der vom User gesehen wird.
    # Der Anzeigename muss zuvor übersetzt werden (translated, siehe tr() Methode).
    def displayName(self):
        return self.tr('Spektren als Graphen')

    # In dieser Methode werden Ein- und Ausgabeparameter definiert und
    # insbesondere welche Eigenschaften diese haben müssen.
    def initAlgorithm(self, config=None):

        # Input soll der Ordner mit den hyperspektralen Daten sein.
        # Auf Klasse des Parameters und die Klassenattribute achten.
        # QgsProcessingParameterFile hat als Attribute Folder oder File.
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT,
                self.tr('Input Ordner mit Daten für die hyperspektrale Spektren'),
                QgsProcessingParameterFile.Folder
            )
        )

    # In dieser Methode wird festgelegt, was der eigentliche Algorithmus tut.
    def processAlgorithm(self, parameters, context, feedback):
        # Den ersten Parameter (Ordnerpfad) als String holen.
        # print(self.parameterAsFile(parameters, "INPUT", context))
        quellordnerpfad = self.parameterAsFile(parameters, "INPUT", context)

        # Einen Iterator auf dem Quellordner erstellen
        obj = os.scandir(quellordnerpfad)

        # Über alle Dateien im Ordner iterieren
        for file in obj:
            if file.is_dir():
                print(file.name + " ist ein Verzeichnis, in welches ich nicht hineinschauen will.")
            elif file.is_file() and file.name.endswith(".rfc"):
                # print(os.getcwd()) # zum überprüfen, ob man bei relativen Pfaden im richtigen Working Directory ist
                # war natürlich im falschen directory, also workingDirectory ändern
                os.chdir(quellordnerpfad)

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

                # Graph: Titel und Achsenbeschriftungen festlegen, dann plotten
                plt.title('Reflexionsspektrum der Probe ' + file.name.replace(".rfc", ""), fontsize=17, color='black')
                plt.xlabel('Wellenlänge [µm]')
                plt.ylabel('Reflexion')
                # Doppelpunkt bedeutet, dass man alle Zeilen bekommt und Index 0 waren die X Werte in dem Array und Index 1 die Y Werte
                plt.plot(graph[:,0],graph[:,1])


                # Verzeichnis kann nur erstellt werden, wenn es noch nicht existiert, ansonsten Fehler
                dirName = "Graphische Spektren"
                if not os.path.exists(dirName):
                    os.mkdir(dirName)
                    print("Das Verzeichnis " , dirName , " wurde erstellt.")

                # Trennzeichen des OS herausfinden mit os.sep und dann den Graphen in dem erstellten Unterordner als png speichern
                plt.savefig('Graphische Spektren' + os.sep + file.name.replace(".rfc", "") + '.png')
                # plt.show()# 100% Absturzgarantie, besser nicht ausführen
                plt.close()

                # --------------------------------------------------------------------------------
                # Continuum Removal bestimmen
                # Index Werte bestimmen, liefert nur die y Werte als 1D Array, x Werte weiterhin aus dem graph array nehmen
                # als parameter zuerst pixel, dann die wellenlänge, je als 1D arrays
                werteHülle = spectro.convex_hull_removal(graph[:,1],graph[:,0])

                # Graphen einstellen
                plt.title('Continuum Removal der Probe ' + file.name.replace(".rfc", ""), fontsize=17, color='black')
                plt.xlabel('Wellenlänge [µm]')
                plt.ylabel('Index')
                plt.plot(graph[:,0],werteHülle[0])

                # ein weiteres Verzeichnis anlegen für die Continuum Removals
                dirName = "Continuum Removal"
                if not os.path.exists(dirName):
                    os.mkdir(dirName)
                    print("Das Verzeichnis " , dirName , " wurde erstellt.")

                # Trennzeichen des OS herausfinden mit os.sep und dann den Graphen in dem erstellten Unterordner als png speichern
                plt.savefig('Continuum Removal' + os.sep + "CR_" + file.name.replace(".rfc", "") + '.png')
                plt.close()

                # CR Werte in eine File schreiben, zuerst einen Unterordner dafür anlegen
                dirName = "Continuum Removal txt"
                if not os.path.exists(dirName):
                    os.mkdir(dirName)
                    print("Das Verzeichnis " , dirName , " wurde erstellt.")
                # neue txt Datei erstellen, w überschreibt die Datei komplett und
                # falls die Datei noch nicht existiert, wird ein eneue Datei angelegt
                f = open('Continuum Removal txt' + os.sep + file.name.replace(".rfc", "") + ".txt", "w")

                # die x und y Werte des Continuum Removal in eine txt Datei schreiben
                # zuerst zwei leere 1D Arrays erstellen
                graphX = np.zeros([anzahlZeilen], dtype=float)
                graphYCR = np.zeros([anzahlZeilen], dtype=float)

                # Array befüllen zuerst für x Werte und dann für y Werte
                for j in range(0, len(graph)):
                    graphX[j] = graph[j][0]
                    graphYCR[j] = werteHülle[0][j]

                for k in range(0, len(graph)):
                    f.write(str(graphX[k]) + " " + str(graphYCR[k]) + "\n")

                #print(type(werteHülle)) # gehört zur Klasse tuple und ist sowas ähnliches wie ein Array
                f.close() # Datei wieder schließen

        # Es muss eine Map mit Ergebnissen zurückgegeben werden (Ergebnisse
        # können statistische Werte oder Layer oder sonstiges sein).
        return {'OUTPUT': 1}


    # Methode liefert einen übersetzbaren String zurück. Diese Methode ist nicht
    # zwingend notwendig, wird aber in der benötigten Methode displayName
    # verwendet. Aufruf mit self.tr("einTollerBeispielString")
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    # Weitere drei Methoden, die nicht zwingend definiert werden müssen, aber im
    # Standard-Template vorhanden sind.
    # Gibt den Gruppennamen, zu der Gruppe, zu welcher das Script gehören soll, zurück.
    def group(self):
        return self.tr('Quanti Scripts')

    # Gibt die GruppenID als String zur Identifikation der Gruppe zurück.
    def groupId(self):
        return 'quantiscripts'

    # Kurzbeschreibung des Skripts.
    def shortHelpString(self):
        return self.tr("Script für die graphische Darstellung der Reflexionsspektren aus den hyperspektralen RFC Dateien."
        + "\n Bevor das Skript gestarted wird, muss das Modul pysptools mit \"pip install pysptools\" über die OSGeo04W Shell installiert worden sein."
        + "\n Der Quellordner wird nicht rekursiv auf Unterordner untersucht, denn wir hassen Rekursion."
        + "\n Das Modul matplotlib ist nicht thread safe und führt daher zu Warnungen sowie beim Starten der GUI zum Absturz."
        + "\n Die Graphen für die normalen Spektren werden in einem Unterordner (namens Graphische Spektren) des angebenen InputOrdners gespeichert."
        + "\n Die Graphen für die Continuum Removal Spektren werden in einem weiteren Unterordner (namens Continuum Removal) abgelegt."
        + "\n Zuletzt werden die X und Y Werte des Continuum Removals in einem dritten Unterordner (namens Continuum Removal txt) gespeichert, damit die Werte zur Verfügung stehen.")
