# Imports: alles was man benutzt, muss man auch einfügen!!!
from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFile)
from qgis import processing
import os
import numpy as np

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
        return 'spektrenalsmultispektralebandwerte'

    # Gibt den Anzeigenamen des Algorithmus zurück, der vom User gesehen wird.
    # Der Anzeigename muss zuvor übersetzt werden (translated, siehe tr() Methode).
    def displayName(self):
        return self.tr('Spektren als multispektrale Bandwerte')

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

                # ----------------------------------------------------------------------------------------------------

                # Mittelwerte berechnen:
                # µm sind die x Werte, durchsuche graph array nach allen x Werten in dem intervall
                nBlau = 0
                nGrün = 0
                nRot = 0
                nNIR = 0
                nMIReins = 0
                nMIRzwei = 0

                summeBlau = 0
                summeGrün = 0
                summeRot = 0
                summeNIR = 0
                summeMIReins = 0
                summeMIRzwei = 0

                # array durchlaufen und nur gewünschten intervalle aufsummieren
                for j in graph:
                    # sichtbares blau
                    if j[0] >= 0.45 and j[0] < 0.52:
                        # werte in diesem Bereich aufaddieren
                        summeBlau = summeBlau + j[1]
                        nBlau = nBlau + 1
                    # sichtbares grün
                    elif j[0] >= 0.52 and j[0] <= 0.60:
                        summeGrün = summeGrün + j[1]
                        nGrün = nGrün + 1
                    # sichtbares rot
                    elif j[0] >= 0.63 and j[0] <= 0.69:
                        summeRot = summeRot + j[1]
                        nRot = nRot + 1
                    # NIR
                    elif j[0] >= 0.76 and j[0] <= 0.9:
                        summeNIR = summeNIR + j[1]
                        nNIR = nNIR + 1
                    # MIReins
                    elif j[0] >= 1.55 and j[0] <= 1.75:
                        summeMIReins = summeMIReins + j[1]
                        nMIReins = nMIReins + 1
                    # MIRzwei
                    elif j[0] >= 2.08 and j[0] <= 2.35:
                        summeMIRzwei = summeMIRzwei + j[1]
                        nMIRzwei = nMIRzwei + 1

                # die sechs Bandwerte berechnen
                blau = summeBlau / nBlau
                grün = summeGrün / nGrün
                rot = summeRot / nRot
                nir = summeNIR / nNIR
                mirEins = summeMIReins / nMIReins
                mirZwei = summeMIRzwei / nMIRzwei

                # Ratios Berechnen:
                eisenOxid = rot / blau
                eisenMinerale = mirEins / nir
                eisen4durch3 = nir / rot
                eisenSumme = eisenOxid + eisenMinerale
                tonEins = mirEins / mirZwei
                tonZwei = (mirEins / mirZwei) / (nir/rot)

                # einen Unterordner für die nun multispektralen Daten anlegen
                dirName = "HyperToMulti txt"
                if not os.path.exists(dirName):
                    os.mkdir(dirName)
                    print("Das Verzeichnis " , dirName , " wurde erstellt.")
                # neue txt Datei erstellen, w überschreibt die Datei komplett und
                # falls die Datei noch nicht existiert, wird ein eneue Datei angelegt
                f = open('HyperToMulti txt' + os.sep + file.name.replace(".rfc", "") + ".txt", "w")

                # die x (Bänder) und y (oben errechnete) Werte in eine txt Datei schreiben
                f.write(str(1) + " " + str(blau) + "\n")
                f.write(str(2) + " " + str(grün) + "\n")
                f.write(str(3) + " " + str(rot) + "\n")
                f.write(str(4) + " " + str(nir) + "\n")
                f.write(str(5) + " " + str(mirEins) + "\n")
                f.write(str(6) + " " + str(mirZwei) + "\n")

                # Ratios mit reinschreiben
                f.write("EisenOxid_3durch1: " + str(eisenOxid) + "\n")
                f.write("EisenMinerale_5durch4: " + str(eisenMinerale) + "\n")
                f.write("EisenAbsorpTiefeNIR_4durch3: " + str(eisen4durch3) + "\n")
                f.write("EisenSumme_(3durch1)plus(5durch4): " + str(eisenSumme) + "\n")
                f.write("Ton_5durch6: " + str(tonEins) + "\n")
                f.write("Ton_(5durch6)durch(4durch3): " + str(tonZwei) + "\n")

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
        return self.tr("Die Hyperspektralen Daten werden über die Mittelwert Bildung in den 6 Bändern in multispektrale Daten überführt."
        + "\n Anschließend werden auf den nun multispektralen Daten die Band Ratios ausgerechnet. Alle Ergebnisse werden in einer txt Datei gespeichert.")
