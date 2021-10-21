---
title: "Applicazione di integrazioni IoT ad un sistema di monitoraggio della qualità dell'aria"
author: |
        | Andrea Cantarutti (141808)
        | Lorenzo Bellina (142544)
date: "20 ottobre 2021"
output:
header-includes:
  - \usepackage{amsmath}
  - \usepackage[margin=0.8in]{geometry}
  - \usepackage[utf8]{inputenc}
  - \usepackage[italian]{babel}
  - \usepackage{graphicx}
  - \usepackage{float}
  - \usepackage{array}
  - \usepackage{multirow} 
  - \usepackage{bigstrut}
  - \usepackage{caption}
---

\captionsetup{labelformat=empty}
\pagenumbering{arabic}
\newpage
\tableofcontents
\newpage

```{=latex}
% introduzione
% il sensore dell'ikea e i dati che misura
% anatomia del sensore e modding del sensore (con costi)
% codice arduino
% architettura docker
% broker mqtt
% logapp
% influxdb
% mqtt app
% funzionamento del bot telegrama
% dashboard e grafici con grafana
% Deployment su raspberry pi (nota su costo raspberry pi)
% Conclusioni e followups (app al posto del bot telegram, possibilità di integrazione con altri sistemi ikea fra cui ad esempio il purificatore)
```

# Introduzione

Il seguente elaborato espone lo sviluppo di un'**integrazione IoT** atta a conferire ad un preesistente strumento per la rilevazione della qualità dell’aria caratteristiche “smart", prevalentemente rivolte allo storage dei dati raccolti, al loro monitoraggio e all'interazione con l'utilizzatore. Il progetto basa su quanto è stato osservato dallo sviluppatore Sören Beye (@Hypfer) che, a seguito di un'attività di *reverse engineering*, ha descritto un procedimento per l'installazione di un modulo ESP8266 all'interno del rilevatore originale, permettendo la raccolta e il processing dei dati rilevati senza alterare le funzionalità di base del sistema.

\newpage

# Il sensore VINDRIKTNING di Ikea

Il strumento di rilevazione di qualità dell'aria utilizzato è un articolo commercializzato da Ikea sotto il nome di **VINDRIKTNING**. Quest'ultimo è in grado di rilevare la quantità di polveri sottili presenti in ambienti chiusi o all'aperto (se contenuti) in base alla classificazione PM 2.5. Sulla base di specifici threshold riportati nel manuale d'uso del sensore, il valore assoluto rilevato permette, rispettivamente, l'accensione di:

- Una luce a led di colore verde atta ad indicare un buon livello di qualità dell'aria
- Una luce a led di colore giallo atta ad indicare un degradamento della qualità dell'aria
- Una luce a led di colore rosso atta ad indicare un pessimo livello di qualità dell'aria.

\begin{figure}[H]
\centering
\includegraphics[width=300px]{img/vindriktning.jpeg}
\end{figure}

Il sensore è costituito da un parallelepipedo in **ABS** di dimensioni pari a 6x6x9 cm. Al suo interno contiene:

- Un sensore **Cubic PM1006**
- Un microcontrollore che si occupa dell'accensione dei led sulla base dei dati rilevati dal sensore 
- Una ventola azionata al fine di favorire il ricircolo dell'aria in prossimità del sensore

VINDRIKTNING non dispone, tuttavia, di ulteriori funzionalità, assestandosi in una fascia di prezzo inferiore a 10€ e venendo spesso proposto a supporto del purificatore d'aria FÖRNUFTIG. 

# Obiettivi e Architettura del sistema 

## Necessità individuate

In seguito all'acquisto di due unità VINDRIKTNING e ad un breve periodo di utilizzo, sulla base delle necessità individute sono stati descritti i seguenti requisiti:

- Possilità di osservare e analizzare l'andamento della qualità dell'aria in un determinato lasso di tempo
- Possibilità di aggregare i dati provenienti da più sensori collocati in diverse stanze
- Facoltà di interrogare i sensori da remoto, ricevendo notifiche nel caso del superamento dei threshold specificati.

## Definizione dei principali servizi

Al fine di poter attuare gli obiettivi preposti, sono stati individuati i principali servizi necessari all'implementazione di un sistema di supporto ad un **flusso di dati** generato da **più sensori** all'interno di una **rete locale**. Si rende, di conseguenza, necessario lo sviluppo di:

- Un **firmware personalizzato** in grado di permettere ai sensori di comunicare in rete le rilevazioni effettuate
- Un servizio centralizzato predisposto alla **ricezione di dati** provenienti da uno o più sensori 
- Un **database** rivolto allo storage e all'interrogazione dei dati raccolti
- Un applicativo di alto livello che, a seguito di una configurazione da parte dell'utente, permette la **fruizione e l'analisi dei dati raccolti** 
- Un sistema in grado **notificare uno o più utenti** in caso di cambiamenti. 
- Un applicativo che permette all'utente il **monitoraggio** e la **configurazione** del funzionamento del sistema

Al fine di favorire in partenza lo sviluppo **indipendente** di ognuno dei servizi sopracitati, si sceglie l'adozione di una strategia basata sull'organizzazione di uno stack multi-container Docker. Tramite quest'ultimi, le risorse possono essere isolate, i processi avviati e gestiti separatamente. Personalizzazioni e modifiche possono, inoltre, essere apportate ad un singolo servizio senza compromettere il funzionamento complessivo del sistema.

\newpage
