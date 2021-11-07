---
title: "Applicazione di integrazioni IoT ad uno strumento per il monitoraggio della qualità dell'aria"
author: |
        | Andrea Cantarutti (141808)
        | Lorenzo Bellina (142544)
date: "8 Novembre 2021"
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

# Introduzione

Il seguente elaborato espone lo sviluppo di un'**integrazione IoT** atta a conferire ad un preesistente strumento per la rilevazione della qualità dell’aria caratteristiche “smart", prevalentemente rivolte allo storage dei dati raccolti, al loro monitoraggio e all'interazione con l'utilizzatore. Il progetto si basa su quanto è stato osservato dallo sviluppatore Sören Beye (@Hypfer) che, a seguito di un'attività di *reverse engineering*, ha descritto un procedimento per l'installazione di un modulo ESP8266 all'interno del rilevatore originale, permettendo la raccolta e il processing dei dati rilevati senza alterare le funzionalità di base del sistema.

\newpage

# Il sensore VINDRIKTNING di Ikea

Lo strumento di rilevazione di qualità dell'aria utilizzato è un articolo commercializzato da Ikea sotto il nome di **VINDRIKTNING**. Quest'ultimo è in grado di rilevare la quantità di polveri sottili presenti in ambienti chiusi o all'aperto (se contenuti) in base alla classificazione PM 2.5. Sulla base di specifici threshold riportati nel manuale d'uso del sensore, il valore assoluto rilevato permette, rispettivamente, l'accensione di:

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

## Caratterizzazione dei requisiti 

In seguito all'acquisto di due unità VINDRIKTNING e ad un breve periodo di utilizzo, sulla base delle necessità individute sono stati descritti i seguenti requisiti:

- Possilità di osservare e analizzare l'andamento della qualità dell'aria in un determinato lasso di tempo
- Possibilità di aggregare i dati provenienti da più sensori collocati in diverse zone dell'abitazione
- Facoltà di interrogare i sensori da remoto, ricevendo notifiche nel caso del superamento dei threshold specificati.

## Definizione dei principali servizi

Al fine di poter attuare gli obiettivi preposti, sono stati delineati i principali servizi necessari all'implementazione di un sistema di supporto ad un **flusso di dati** generato da **più sensori** connessi allo stesso dispositivo. Si rende, di conseguenza, necessario lo sviluppo di:

- Un **firmware personalizzato** in grado di permettere ai sensori di comunicare via rete le rilevazioni effettuate
- Un servizio per la **ricezione centralizzata dei dati**
- Un **database** adibito allo storage e all'interrogazione dei dati raccolti
- Un applicativo rivolto alla **fruizione** dei dati raccolti e alla **configurazione** del sistema
- Un servizio per la **notifica di uno o più utenti** in caso di cambiamenti notevoli. 

Al fine di favorire in partenza lo sviluppo **indipendente** di ognuno dei servizi sopracitati, è stata addottata una strategia implementativa basata sull'organizzazione e la coordinazione di molteplici container. Tramite quest'ultimi, infatti, le risorse possono essere isolate e i processi avviati e gestiti separatamente. Personalizzazioni e modifiche possono, inoltre, essere apportate senza compromettere il funzionamento complessivo del sistema.

Si descrivono, di seguito, le tecnologie adottate e le implementazioni svolte al fine di attuare l'architettura descritta.

# Modifiche e personalizzazioni apportate a VINDRIKTNING

## Obiettivi

Al fine di permettere a VINDRKTNING una regolare comunicazione via rete della qualità dell'aria rilevata, è stata adottata una strategia basata su **protocollo MQTT**. In questo modo, ogni sensore connesso alla rete comunica, in qualità di **publisher**, aggiornamenti costanti ad un **broker** appositamente predisposto. Tale soluzione permette, inoltre, l'introduzione di nuovi sensori senza richiedere specifiche configurazioni e/o il riavvio del sistema.

## Personalizzazione dell'hardware 

Come precedentemente specificato, le modifiche apportate all'hardware del sensore si basano sull'attività di reverse engineering svolta dallo sviluppatore Sören Beye (@Hypfer) e accuratamente documentata su GitHub.

Una volta aperto il contenitore di VINDRIKTNING svitando le quattro viti che lo mantengono chiuso, è immediatamente visibile un microcontrollore adibito all'accensione dei led, al quale sono connessi, per mezzo di appositi connettori:

- Il sensore **Cubic PM1006** (la cui rilevazione viene letta tramite protocollo seriale)
- La sottostante ventola per il ricircolo dell'aria. 

\begin{figure}[H]
\centering
\includegraphics[width=250px]{img/sensore1}
\end{figure}

Si osserva, inoltre, come la breakout board del microcontrollore presenti svariati pin inutilizzati, fra cui: 

- `+5V` e `GND` (passthrough per l'alimentazione ricevuta tramite cavo USB)
- `ISPDA` e `ISPCLK` (che forniscono una connessione ai pin SCL e SDA per la comunicazione tramite protocollo I2C)
- `REST` (che fornisce un test point per il pin seriale `RX`)
- `LED_G_1` e `LED_R_1` (che forniscono un punto d'accesso per la comunicazine con led appositi)
- `PWM_Fan`, `FAN-` e `FAN+` (che permettono l'alimentazione e il controllo della velocità della ventola tramite segnali PWM)

\begin{figure}[H]
\centering
\includegraphics[width=55px]{img/breakout.png}
\end{figure}

Risulta, di conseguenza, possibile la connessione di un'unità esterna che, una volta saldata ai pin di alimentazione (`+5V` e `GND`) e al test point seriale `REST`, permette l'acquisizione del valore rilevato dal sensore **PM1006** e letto dal microcontrollore originale. In particolare, è stata selezionata un'unità **ESP8266** (nello specifico, un clone del **D1 Mini by Wemos** prodotto da AZDelivery), che in dimensioni estremamente ridotte fornisce:

- La possibilità di essere alimentata a 5V grazie al regolatore di tensione built-in (e quindi di ricevere la corrente di alimentazione direttamente dalla porta USB di VINDRIKTNING)
- La connettività via Wi-Fi in modalità Access Point e Station Mode, entrambe necessarie allo sviluppo previsto 
- La possibilità di essere programmato tramite il framework **Arduino**, con il conseguente accesso alla moltitudine di librerie disponibili in rete

Cavi dupont appositamente modificati sono stati saldati ai punti di accesso citati in precedenza, ottenendo il seguente risultato. 
\begin{figure}[H]
\centering
\includegraphics[width=400px]{img/dupont.png}
\end{figure}

Infine, i seguenti pin del modulo D1 mini sono stati impiegati per effettuare la connessione: 

| D1 Mini | Punto di Accesso |
|---------|------------------|
|  `+5V`  |  `+5V`           |
|  `GND`  |  `GND`           |
|  `D2`   |  `REST`          |

\newpage

VINDRIKTNING permette, infine, l'alloggiamento del modulo al suo interno, grazie all'ampio spazio disponibile. 

\begin{figure}[H]
\centering
\includegraphics[width=300px]{img/full.jpeg}
\end{figure}

## Costo di realizzazione

Le modifiche apportate hanno coinvolto l'utilizzo dei seguenti materiali: 

- Unità VINDRIKTNING originale
- Cavi dupont
- Cacciavite di tipo `PH0` per l'apertura del vano posteriore 
- Strumentazione per la saldatura
- Modulo ESP8266 (D1 Mini by Wemos)

Al netto dell'attrezzatura già in possesso, il costo necessario all'apporto delle modifiche sopracitate viene di seguito descritto:

| Componente | Costo Individuale | Quantità acquistate |
|------------|------------------:|--------------------:|
| VINDRIKTNING |  9,95 €         |     2               |
| D1 Mini    |    4,00 €         |     2               |
| Cavi Dupont|    3,00 €         |     1               |

Il costo coinvolto nella personalizzazione di una singola unità VINDRIKTNING corrisponde, quindi, alla cifra di **16,95 €**. La personalizzazione di due unità richiede, invece, una spesa complessiva pari a **30,90 €**.

## Implementazione di un firmware ad-hoc

A seguito dell'installazione del modulo D1 Mini è stato sviluppato un firmware parzialmente ispirato a quello proposto da Sören Beye, con l'obiettivo di fornire le seguenti funzionalità: 

- Lettura e decodifica del payload inviato dal sensore sulla porta seriale
- Semplice procedura per la configurazione e la connessione di VINDRIKTNING alla rete Wi-Fi
- Persistenza dei parametri di configurazione anche in caso di riavvio del dispositivo
- Possibilità di eseguire aggiornamenti del firmware da remoto, senza richiedere la riapertura del contenitore
- Invio regolare dei dati ad un broker MQTT appositamente configurato

### Decodifica del payload

Al fine di memorizzare efficacemente ogni singola rilevazione, viene mantenuta la struttura dati di seguito descritta.

```cpp
struct particleSensorState_t {
    uint16_t avgPM25 = 0;                          
    uint16_t measurements[5] = {0, 0, 0, 0, 0};    
    uint8_t measurementIdx = 0;                    
    boolean valid = false;                         
    uint8_t status = 0;                            
};
```

Quest'ultima incapsula un insieme di cinque misurazioni (svolte consecutivamente per aumentare la precisione della rilevazione), la loro media e ulteriori flag che indicano la classe di qualità rilevata dal sensore e la validità della misurazione. Il sensore viene regolarmente interrogato dal microcontrollore originale, inviando in risposta un payload di 20 byte. Di questi:

- I primi tre sono costanti (in caso di payload valido) e costituiscono l'**header** 
- I byte `5` e `6` codificano il valore di qualità dell'aria rilevato

Il namespace `SerialCom` contenuto all'interno dell'header file `Utils.h` fornisce le funzionalità per:

- Leggere i dati dalla porta seriale (configurata tramite SoftwareSerial sul pin 2D del modulo ESP8266) all'interno di un buffer
- Effettuare cinque letture consecutive del valore di qualità dell'aria, calcolandone la media
- Individuare la classe di qualità alla quale appartiene il valore medio rilevato
- Verificare la validità dell'header (i cui tre byte devono corrispondere a `0x16 0x11 0x0B`)
- Verificare la validità del checksum (la somma dei venti byte deve essere pari a 0)

In particolare, l'ottenimento del numero intero (codificato da due byte) relativo alla misurazione di PM2.5 da parte del sensore viene permesso dalla seguente operazione bitwise, che applica un padding destro di 8 bit al primo byte e, successivamente, effettua un `OR` tra il primo e secondo byte. Il risultato, una volta codificato come dato di tipo `uint16_t`, viene salvato nell'apposita struttura dati `struct particleSensorState_t`.

```c
const uint16_t pm25 = (serialRxBuf[5] << 8 | serialRxBuf[6]);
```


### Salvataggio e recupero dei parametri di configurazione

Al fine di rendere disponibile il salvataggio dei parametri di configurazione personalizzabili e il loro successivo recupero in seguito ad un eventuale riavvio del microcontrollore, all'interno dell'headerfile `Utils.h` il namespace `Config` definisce due funzioni che permettono, rispettivamente, di serializzare i parametri di configurazione in un file JSON all'interno della memoria flash del dispositivo e di leggere i parametri a partire da un eventuale file già presente in memoria. 

Ciò è reso possibile dalla libreria **LittleFS**, che permette l'indicizzazione di un filesystem all'interno della memoria flash del dispositivo (la quale risulta avere una capienza pari a 4MB) tramite tecniche di wear levelling dinamico che ne limitano l'usura.

### Aggiornamento del firmware da remoto

L'aggiornamento via rete del firmware è reso possibile dalla libreria **ArduinoOTA** (On The Air), che permette di istruire il microcontrollore alla ricezione di nuovi binari precompilati tramite una socket TCP appositamente aperta.

Successivamente, è stato possibile inoltrare aggiornamenti al microcontrollore tramite il seguente comando disponibile nel framework offerto da **PlatformIO**:

```bash
pio run --target upload --upload-port [VINDRIKTNING-IP] 
```

La risposta ottenuta dipende dalla configurazione di ArduinoOTA all'interno della funzione di setup. L'aggiornamento di VINDRIKTNING presenta il seguente output: 

\begin{figure}[H]
\centering
\includegraphics[width=500px]{img/arduinoOTA.png}
\end{figure}

Al fine di prevenire upload accidentali, è stata definita una password che viene richiesta per completare la procedura di aggiornamento.

### Configurazione di parametri personalizzati

Per permettere all'utilizzatore il collegamento alla propria rete e la configurazione di parametri per la comunicazione con il Broker MQTT, è stata impiegata la libreria **WiFiManager**. Quest'ultima permette, sulla base della presenza o assenza di una rete WiFi alla quale il microcontrollore è in grado di connettersi, la conversione automatica del modulo ESP8266 da modalità **SoftAccessPoint** a **Station** e viceversa. 

In modalità SoftAccessPoint, è possibile connettersi direttamente al microcontrollore, che espone una pagina web la quale permette all'utente di effettuare lo scan delle reti disponibili, la connessione ad una rete specifica e la configurazione dei parametri personalizzabili. Nel caso di VINDRIKTNING, l'utente ha la facoltà di specificare:

- L'indirizzo IP del Broker MQTT
- La porta del Broker MQTT
- Il nome utente e la password per inviare messaggi al Broker
- Un nome da assegnare allo specifico sensore (ad esempio, *Cucina*)

La schermata di configurazione visualizzata da uno smartphone è la seguente:

\begin{figure}[H]
\centering
\includegraphics[width=150px]{img/phone2.PNG}
\end{figure}

Nel caso in cui la connessione alla rete WiFi selezionata vada a buon fine, il modulo passa automaticamente a modalità Station ed entra a far parte degli host connessi alla rete specificata. I dati ottenuti da WiFiManager vengono, infine, serializzati in memoria flash tramite le funzionalità precedentemente descritte. In questo modo, non si rende necessario ripetere la procedura a fronte di un semplice riavvio del sistema.

### Comunicazione con il Broker MQTT

La gestione della connessione e dell'invio di messaggi al Broker MQTT è stata, invece, affidata alla liberia **PubSubClient**. Ad intervalli specificati dalla macro `MQTT_PUBLISH_INTERVAL_MS`, un'eventuale rilevazione valida viene inviata al Broker sull'apposito topic di aggiornamento dello stato di qualità dell'aria. Nel caso di assenza di connettività, invece, il sistema tenta regolarmente una riconnessione finché questa non risulta avvenuta. 

Due ulteriori messaggi vengono, infine, comunicati al broker al momento della connessione:

- Dichiarazione di **connessione** da parte di VINDRIKTNING al Broker
- Dichiarazione di **testamento** da parte di VINDRIKTNING al Broker

Quest'ultima permette la definizione di uno specifico messaggio con flag di ritenzione attiva che viene inviato dal broker a tutti i **subscriber** in caso di una brusca ed imprevista disconnessione da parte del sensore. 

Al fine di fornire ad ogni sensore un identificatore univoco per agevolarne la comunicazione con il broker, viene descritto un apposito **sensorID** costituito dalla stringa `VINDRIKTNING-[chip-id]`, dove `chip-id` rappresenta l'**UUID** del modulo ESP8266. Di conseguenza, nonostante il nome a livello utente sia quello dichiarato nell'apposito campo "Name", un ulteriore identificativo viene reso disponibile al fine di poter individuare rapidamente il sensore nell'insieme di quelli connessi alla rete. 

Sulla base dell'identificatore univoco di ogni sensore, i topic coinvolti risultano, quindi, i seguenti:

1. `airquality/[sensorID]/online` (Connessione del sensore identificato da `[sensorID]`)
2. `airquality/[sensorID]/offline` (Disconnessione del sensore identificato da `[sensorID]`)
1. `airquality/[sensorID]/status` (Nuova rilevazione dal sensore identificato da`[sensorID]`)

Il codice sorgente del firmware implementato risulta accessibile all'interno del progetto PlatformIO contenuto all'interno della directory `firmware`.

# Definizione del Broker MQTT

Al fine di poter comunicare i dati sulla rete, VINDRIKTNING necessita di un indirizzo valido che identifichi un **Broker MQTT** adibito alla ricezione e all'eventuale ritenzione dei messaggi. A tal fine, è stata scelta l'adozione del software open source **Eclipse Mosquitto**.

## Containerizzazione di Eclipse Mosquitto

Sulla base delle decisioni architetturali riportate in precedenza, è stato scelto di eseguire Eclipse Mosquitto all'interno di un container **Docker**, sfruttando l'immagine ufficiale.

|
|

```Dockerfile

FROM eclipse-mosquitto

ADD ./config/mosquitto.conf /mosquitto/config
ADD ./broker-entrypoint.sh /

ENTRYPOINT ["sh", "./broker-entrypoint.sh"]

CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]

```

|
|

A partire dall'immagine disponibile dal repository di *Docker Hub*, sono stati aggiunti:

- Il file `mosquitto.conf`, che letto all'avvio del servizio permette: 
	- L'abilitazione della persistenza dei dati all'interno di un'apposita directory interna al container
	- La definizione di una destinazione per i file di log scritti dal Broker
	- La specifica della porta utilizzata e di un modello di autenticazione

|
|

```bash
    
persistence true
persistence_location /mosquitto/data

user mosquitto

log_dest file /mosquitto/log/mosquitto.log
log_dest stdout

listener 1883
allow_anonymous true
password_file passwordfile

```

\newpage

- Lo script `broker-entrypoint.sh` (eseguito come entrypoint all'avvio), la cui esecuzione comporta:
	- L'attribuzione dei corretti permessi alle cartelle relative alla configurazione di Mosquitto
	- La verifica della presenza di un nome utente e una password all'avvio del container
	- La definizione delle credenziali tramite l'utility `mosquitto_passwd`

|
|

```bash
set -e

# Fix write permissions for mosquitto directories
chown --no-dereference --recursive mosquitto /mosquitto/log
chown --no-dereference --recursive mosquitto /mosquitto/data

mkdir -p /var/run/mosquitto \
  && chown --no-dereference --recursive mosquitto /var/run/mosquitto

if ( [ -z "${MOSQUITTO_USERNAME}" ] || [ -z "${MOSQUITTO_PASSWORD}" ] ); then
  echo "MOSQUITTO_USERNAME or MOSQUITTO_PASSWORD not defined"
  exit 1
fi

# create mosquitto passwordfile
touch passwordfile
mosquitto_passwd -b passwordfile $MOSQUITTO_USERNAME $MOSQUITTO_PASSWORD

exec "$@"
```

|
|

\newpage

# Definizione di un database per lo storage dei dati

## Scelta del DBMS

Al fine di permettere il salvataggio e la successiva fruizione dei dati, è stata impiegata una base di dati organizzata come servizio indipendente, anch'esso containerizzato. In particolare, è stata scelta l'adozione del DBMS **InfluxDB** in risposta alle seguenti necessità:

- Organizzazione dei dati orientata ai **timestamp** 
- Definizione di una **retention policy** al fine di permettere l'eliminazione dei dati al di fuori del periodo di interesse 

## Containerizzazione 

La containerizzazione del servizio ha richiesto la sola definizione del seguente Dockerfile che, nello specifico, prevede l'inclusione di un opportuno script di inzializzazione all'interno dell'immagine **InfluxDB** originale al fine di inizializzare il database utilizzato e la retention policy.

|
|

```Dockerfile

FROM influxdb:1.8
ADD ./createdb.iql /docker-entrypoint-initdb.d/

```

|
|

In particolare, lo script `createdb.iql` (il cui contenuto è di seguito riportato) prevede la definizione di:

- Un database denominato `airquality` con retention-policy pari a 7 giorni
- Un utente con permessi di scrittura e lettura sulla base di dati
- Un utente con permessi di sola lettura sulla base di dati 

|
|

```sql

CREATE DATABASE airquality WITH DURATION 7d
CREATE USER api WITH PASSWORD 'apisecret'
CREATE USER reader WITH PASSWORD 'read'
GRANT READ ON airquality to api 
GRANT READ ON airquality to reader 
GRANT WRITE ON airquality to api 

```

|
|

Una volta avviato, il servizio risulterà disponibile all'uso ed accessibile tramite la porta **8086** del container.

\newpage

# AirPI

Al fine di fornire uno strumento rivolto alla **fruizione** e **ricezione centralizzata dei dati**, oltre che all'invio di **notifiche in tempo reale** all'utilizzatore, è stato implementato il servizio **AirPI**. Quest'ultimo è costituito da un'API di tipo REST (implementata tramite il microframework Flask) abilitata alla ricezione dei dati trasmessi dai sensori, che può essere amministrata e configurata da uno o più utenti tramite un apposito applicativo web-based denominato **VINDRKTNING Station - Monitoring Tool**.

## Ricezione dei dati tramite protocollo MQTT

L'implementazione di AirPI prevede la definizione di un **subscriber MQTT** implementato tramite il middleware **Flask-MQTT**, che fornisce un wrapper rivolto all'integrazione della libreria **Paho MQTT Client** in **Flask**. 

In particolare, la configurazione del client MQTT è permessa dalle seguenti variabili d'ambiente, appositamente associate ai rispettivi parametri definiti all'interno del codice sorgente:

- `MOSQUITTO_USERNAME` (nome utente necessario alla comunicazione con il Broker MQTT)
- `MOSQUITTO_PASSWORD` (password necessaria alla comunicazione con il Broker MQTT)

L'implementazione prevede, quindi:

- L'iscrizione al topic `airsensor/#`
- La gestione e lo storage dei messaggi ricevuti tramite un'apposita routine identificata dal decoratore `@mqtt.on_message()`

Nello specifico, i dati ricevuti permettono l'aggiornamento dell'ultimo stato noto del sensore e l'eventuale esecuzione di opportune query di inserimento (tramite la libreria **InfluxDB Client**) al fine di serializzare i dati ricevuti (corredati di apposito timestamp) all'interno del database.

## Autenticazione

Al fine di garantire l'amministrazione del sistema ai soli utenti autorizzati, AirPI presenta un sistema di **autenticazione** basato su **JSON Web Tokens**, implementato tramite il middleware **flask_jwt_extended**.

Eventuali richieste agli endpoint richiedono, pertanto, la presenza di un apposito **token** all'interno dell'header della richiesta. Quest'ultimo presenta una durata limitata e può essere richiesto, in cambio di valide credenziali, interrogando l'endpoint `/api/auth`.

## Notifica degli utenti

### Bot Telegram 

Al fine di poter notificare gli utenti in tempo reale nel caso di variazioni notevoli della qualità dell'aria misurata dai sensori, è stato definito un **Bot Telegram** in grado di:

- Comunicare variazioni di qualità tramite messaggi inviati agli utenti iscritti
- Permettere agli utenti la verifica dello stato del sistema tramite semplici comandi

### Implementazione 

Considerato il limitato insieme di funzionalità necessarie, l'implementazione del bot non si appoggia a librerie esterne ed è consultabile al percorso file `airpi/app/bot.py`. In particolare, la ricezione di nuovi messaggi avviene tramite una costante attività di **long polling** all'endpoint `getUpdates` dell'API di Telegram, mentre l'invio di eventuali risposte e notifiche avviene tramite apposite richieste all'endpoint `sendMessage`.

Il bot può essere istanziato come di seguito, utilizzando come **token** quello fornito da **BotFather** in seguito alla procedura di creazione del bot:

```python

from bot import Bot

b = Bot('token-provided-by-telegram')

```

|
|

Successivamente, è possibile definire apposite funzioni di callback da eseguire in seguito alla ricezione di specifici messaggi. In particolare, la specifica avviene secondo lo schema seguente.

```python

def callback_routine(chat_id, username, params):
	# pass

b.on('/command', callback_routine)

```

|
|

L'invio di messaggi è, infine, reso disponibile tramite il metodo `push_notification`, che prevede la presenza di due parametri in riferimento al contenuto del messaggio e al gruppo di uno o più utenti a cui recapitarlo (identificati dal rispettivo chat id). 

```python

b.push_notification('message', [chat_id1, ..., chat_idN])

```

### Comandi implementati

Sulla base delle funzionalità necessarie, nel caso di AirPI sono stati implementati i seguenti comandi:

- `/status` (permette all'utente di ottenere informazioni sullo stato dei sensori noti)
- `/info [sensorName]` (permette di ottenere l'ultima rilevazione effettuata da sensori avente nome corrispondente)
- `/bind` (permette agli utenti abilitati di attivare la ricezione di notifiche)
- `/start` (permette l'invio di un messaggio all'inizio della conversazione)

### Invio di notifiche

L'invio di specifici messaggi di notifica avviene in seguito alla rilevazione di variazioni notevoli misurate da un sensore. Viene, quindi, specificato il messaggio da trasmettere a tutti gli utenti che hanno, in precedenza, eseguito il comando `/bind`. In particolare, è previsto l'invio di uno dei seguenti messaggi ad ogni variazione di **classe di qualità** rilevata da un'unità VINDRKTNING:

| Messaggio | Classe di qualità |
|-----------|-------------------|
|The air quality in [sensorName] is getting good | 0 |
|The air quality in [sensorName] is getting unpleasant | 1 |
|The air quality in [sensorName] is getting unacceptable | 2 |

### Esempio di conversazione

Di seguito viene riportato un esempio di conversazione, nel corso della quale: 

1. Viene eseguito il comando `/start` (chiamato automaticamente all'inizio di una conversazione con un bot)
2. Viene eseguito il comando `/bind`
3. Viene richiesto lo stato dei sensori noti
4. Vengono richieste informazioni relative al sensore `Camera2`
5. Viene ricevuta una notifica relativa ad un peggioramento della qualità dell'aria

\begin{figure}[H]
\centering
\includegraphics[width=200px]{img/conversation.png}
\end{figure}

Si osserva, in particolare, come in risposta al comando `/info` l'utente riceva in risposta i parametri:

- **Sensor Name** (nome del sensore in questione) 
- **Quality** (classe di qualità rilevata, rappresentata dal rispettivo colore attualmente attivo sul sensore)
 - **Value** (valore assoluto relativo alla misurazione PM2.5 effettuata dal sensore) 

Questi ultimi vengono ottenuti per mezzo della seguente query InfluxDB che, eseguita tramite InfluxDBClient, permette di ottenere la più recente rilevazione serializzata nel corso dell'ultimo minuto in relazione ad uno specifico sensore:

|
|

```sql
SELECT last("pm25"), "quality" 
FROM "airquality" 
WHERE time > now() - 1m AND 
"name"=sensorName
```

|
|

Inoltre, si specifica come la trasmissione di notifiche coincida con il superamento di specifiche soglie (indicate nel manuale d'uso di VINDRIKTNING) per le quali consegue il cambiamento del colore identificativo della qualità rilevata.

Infine, l'invio di messaggi non riconosciuti e/o malformati, oppure l'invio di messaggi da parte di utenti non autorizzati, non solleva alcuna reazione da parte del bot.

## Gestione delle utenze

### Integrazione di un database relazionale

Al fine di memorizzare le **credenziali** relative agli utenti in grado di accedere all'applicativo web-based e i **nominativi** degli utenti telegram in grado di interagire con il bot telegram, è stato integrato l'utilizzo di un database relazionale all'interno dell'implementazione di AirPI. 

In particolare, è stato impiegato un DBMS SQLite (il cui file di riferimento risulta disponibile al percorso file `/airpi/app/appdb.db`) interrogato per mezzo delle funzionalità fornite dalla liberia **SQLAlchemy** che, in qualità di Object Relational Mapper, permette l'interazione con un generico database relazionale sfruttando caratteristiche proprie del paradigma Object Oriented (facilitando, così, un'eventuale transizione ad un DBMS diverso).

### Gestione degli utenti Telegram

La tabella `telegram_user` della base di dati permette la memorizzazione, tramite apposita richiesta da parte di un utente amministratore, di uno o più nomi utenti relativi a profili Telegram ai quali viene a tutti gli effetti concessa la facoltà di dialogare con il bot implementato. Tuttavia, come delinato in precedenza, il salvataggio nel database del **chat id** relativo ad ogni utente avviene solamente in seguito all'esecuzione del comando `/bind` da parte dell'utente stesso. Tale strategia fornisce una forma di sicurezza **bidirezionale**, in quanto garantisce: 

- Che utenti non abilitati non possano comunicare con il bot
- Che un amministratore non possa sfruttare il bot per inviare messaggi indesiderati

Il modello SQLAlchemy definito per la tabella è il seguente: 

```python
class TelegramUser(db.Model):
    username = db.Column(db.String(50), primary_key=True)
    chat_id = db.Column(db.Integer, nullable=True)
```

### Gestione degli utenti di Monitoring Tool

La tabella `user` della base di dati permette, invece, la memorizzazione degli utenti abilitati ad accedere al servizio Monitoring Tool. In particolare, per ogni utente vengono definiti: 

- Un nome utente univoco
- Una password (della quale viene memorizzato un hash computato tramite l'utilizzo di SHA256+Salt)
- Una flag che definisce se l'utente è di tipo amministratore o meno.

In particolare, gli utenti amministratori si distinguono da quelli regolari in quanto: 

- Presentano la possibilità di aggiungere e rimuovere utenti, o di modificarne le credenziali
- Presentano la possibilità di abilitare e disabilitare utenti al dialogo con il bot telegram

Il modello SQLAlchemy definito per la tabella è il seguente: 

```python
class User(db.Model):
    id = db.Column(db.Integer, db.Sequence('user_id_seq'), primary_key=True)
    name = db.Column(db.Text, unique=True)
    password = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
```

### Struttura della directory

L'implementazione di AirPI è contenuta all'interno del percorso file `airpi/app` e prevede la presenza dei seguenti file:

- `app.py` (contenente l'implementazione di AirPI)
- `bot.py` (contenente l'implementazione del Bot Telegram)
- `first_user.py` (contenente uno script finalizzato all'inizializzazione del primo utente del database)
- `appdb.db` (contenente il database SQLite utilizzato per gestire le utenze)
- `static`
	- `static/css` (directory contenente i file CSS utilizzati da Monitoring Tool)
	- `static/img` (directory contenente le immagini utilizzate da Monitoring Tool)
	- `static/js` (directory contenente gli script e le librerie JavaScript utilizzate da Monitoring Tool)
- `templates` (directory contenente i template HTML descrtti tramite Jinja2)

## Monitoring Tool

Come riportato in precedenza, al fine di fornire uno strumento rivolto alla fruizione dei dati raccolti dai sensori e all'amministrazione delle utenze del sistema è stato definito un applicativo web-based denominato **Monitoring Tool**.

L'implementazione dell'app si appoggia alla libreria di templating HTML **Jinja2** integrata in Flask, che permette di inviare al richiedente pagine HTML appositamente formattate. Queste ultime sfruttano, a loro volta, richieste **fetch** (implementate lato client utilizzando il linguaggio JavaScript) per interrogare gli endpoint di AirPI rivolti all'ottenimento delle informazioni necessarie. Al fine di ottenere un layout responsive è stato utilizzato il framework **Bootstrap 4**, al quale sono state apportate minime integrazioni all'interno di un apposito foglio di stile.

Le funzionalità implementate, in particolare, prevedono: 

- Una homepage che, a seguito di una corretta autenticazione da parte dell'utente, permette la visualizzazione di grafici riassuntivi in relazione all'andamento della qualità dell'aria nelle ultime 24 ore
- Una pagina per l'aggiunta e la rimozione di utenti Telegram in grado di dialogare con il bot (accessibile solo ad utenti amministratori)
- Una pagina per la creazione, modifica e rimozione di utenti (accessibile solo ad utenti amministratori)
- Una pagina per la modifica delle credenziali relative al proprio profilo 
- Una pagina per permettere il log-in agli utenti autorizzati


### Barra di Navigazione

L'accesso alle funzionalità previste da **Monitoring Tool** è permesso dall'apposita barra di navigazione, che presenta un insieme di opzioni diverse sulla base del livello di autenticazione dell'utente. In particolare,

- Nel caso di utenti non autenticati, non risulta presente alcuna voce
- Nel caso di utenti autenticati e non amministratori, risultano accessibili:
	- La pagina principale
	- La pagina di configurazione del profilo
	- L'opzione di Logout
- Nel caso di utenti autenticati e amministratori, risultano accessibili:
	- La pagina principale
	- La pagina di configurazione delle utenze Telegram
	- La pagina di configurazione delle utenze di Monitoring Tool
	- La pagina di configurazione del profilo
	- L'opzione di Logout

In particolare, ad ogni pagina corrisponde uno specifico endpoint di AirPI:

| Pagina | Endpoint |
|--------|----------|
| Homepage | `/`    |
| Login  | `/login` |
| Configurazione utenti  | `/users` |
| Configurazione utenti telegram  | `/telegram` |
| Configurazione profilo  | `/me` |
| Logout | `/logout` |



### Homepage

La pagina principale (accessibile solamente a seguito di un'autenticazione da parte di utenti amministratori e non) risulta incentrata sulla visualizzazione di due grafici (selezionabili per mezzo degli appositi selettori) riportanti: 

- L'andamento della qualità dell'aria per ogni sensore noto nelle ultime 24 ore (nel caso del diagramma a linee)
- La qualità media rilevata da ogni sensore nel corso delle ultime 24 ore (nel caso del diagramma a barre)

L'implementazione dei grafici, in particolare, si appoggia alle librerie **chart.js**, **moment.js** e **chartjs-plugin-colorschemes.js**. Il loro popolamento si basa, invece, su apposite richieste `HTTP` di tipo `GET` effettuate agli endpoint `/api/data/line` e `/api/data/bar` definiti da AirPI e accessibili solo previa autenticazione. Questi ultimi prevedono: 

- L'esecuzione di una query parametrizzata all'interno del database InfluxDB
- L'organizzazione della risposta in un array di oggetti JSON
- La trasmissione dei dati in risposta alla richiesta

La **query** impiegata per l'ottenimento dei dati necessari alla produzione del diagramma a linee è la seguente: 

|
|

```sql
SELECT mean("pm25") 
FROM "airquality" 
WHERE time > now() - 24h 
GROUP BY time(10m), "name" 
fill(none)'
```

|
|

In particolare, la restituzione del valore medio per ogni intervallo di dieci minuti prevista dalla query fornisce un livello di **aggregazione** dei dati serializzati all'interno del database al fine di ridurre la mole di informazioni trasmesse e, successivamente, utilizzate per la produzione e renderizzazione del grafico.

La query impiegata per l'ottenimento dei dati necessari alla produzione del diagramma a barre è, invece, la seguente: 

|
|

```sql
SELECT mean("pm25")
FROM "airquality" 
WHERE time > now() - 24h 
GROUP BY "name"
```

|
|

La visualizzazione ottenuta consultando la pagina principale è la seguente: 

\begin{figure}[H]
\centering
\includegraphics[width=380px]{img/lineplot.png}
\caption{Lineplot raffigurante l'andamento della qualità dell'aria rilevata}
\end{figure}

|
|

\begin{figure}[H]
\centering
\includegraphics[width=380px]{img/barplot.png}
\caption{Barplot raffigurante la qualità media rilevata per ogni sensore}
\end{figure}

Il tracciato individuato dai sensori "Camera2" e "Cucina", in particolare, risulta quasi sempre analogo a causa della stretta vicinanza fra i due sensori in fase di misurazione. Inoltre, il picco osservato nell'orario corrispondente alle `19:00` è dovuto alla presenza di fumo di sigaretta all'interno della stanza.

### Gestione degli utenti Telegram

La pagina relativa all'abilitazione degli utenti telegram prevede la renderizzazione di un'apposita tabella riportante gli **utenti attualmente abilitati** con annesso **chat id** (se disponibile). Inoltre, la rimozione di un utente è permessa a seguito di un click sull'apposito pulsante di eliminazione dell'utente, mentre l'aggiunta di un nuovo utente è permessa dal form modale accessibile clickando il pulsante riportante la scritta **Add a User**. Quest'ultimo propone un menu a comparsa che permette all'utente di digitare il nome utente da abilitare e inviare la richiesta.

Le operazioni di aggiunta di un nuovo utente, rimozione di un utente esistente e di ottenimento di tutti gli utenti attualmente abilitati sono permesse dall'endpoint `/api/telegram` di AirPI, interrogato rispettivamente da richieste `HTTP` di tipo `POST`, `DELETE` e `GET`. 

In particolare, a seguito di ogni richiesta vengono apportate le dovute modifiche all'interno della tabella **TelegramUser** del database relazionale impiegato per l'organizzazione delle utenze.

### Gestione degli utenti di Monitoring Tool

La pagina relativa all'inserimento, rimozione e modifica degli utenti di Monitoring Tool, similmente a quanto illustrato nel caso degli account Telegram, prevede il popolamento di una tabella riportante, per ogni utente, il relativo nome assieme ad un indicatore riferito all'eventuale possesso dei permessi di amministrazione. La rimozione di un utente è possibile tramite l'apposito pulsante di eliminazione, mentre la modifica delle informazioni è permessa da un form modale accessibile clickando sul pulsante di configurazione. La creazione di un nuovo utente è, infine, possibile tramite il form accessibile clickando sul pulsante riportante la scritta **Add New Profile**.

Le operazioni di visualizzazione, aggiunta, modifica e rimozione di un utente sono permesse dall'endpoint `/api/users` di AirPI, interrogato rispettivamente da richieste `HTTP` di tipo `GET`, `POST`, `PUT` e `DELETE`. In particolare, a seguito di ogni richiesta vengono apportate le dovute modifiche all'interno della tabella **User** del database relazionale impiegato per l'organizzazione delle utenze.

L'endpoint `/api/me` di AirPI permette, infine, ad utenti amministratori e non di apportare modifiche in relazione alle **sole** credenziali del proprio profilo, senza poter variare, però, il livello di permessi associato all'utente.

## Installazione di un server WSGI

### Gunicorn 

Nonostante Flask permetta l'esecuzione di un server di sviluppo tramite l'utility `flask run`, è stato scelto di eseguire AirPI per mezzo di un server di produzione di tipo WSGI al fine di garantire maggiore efficienza, stabilità e sicurezza da parte dell'applicativo. È stata, quindi, impiegata la libreria **gunicorn** che, una volta installata tramite `pip`, permette l'esecuzione di un'app Flask sfruttando il comando

```bash
gunicorn app:app -w 1 --bind 0.0.0.0:5000
```

### Definizione di un servizio di Reverse Proxy

Con l'obiettivo di garantire una connessione sicura è stato definito un servizio di **reverse proxy** tramite un web server **nginx** dedicato.

In particolare, l'obiettivo di quest'ultimo è quello di redirezionare le richieste al web server WSGI di AirPI e trasmettere le risposte ottenute tramite una connessione sicura con l'utente finale. La configurazione del reverse proxy prevede, inoltre, la redirezione di richieste `HTTP` ad `HTTPs`.

I certificati necessari all'apertura di una connessione sicura possono essere generati:

- Manualmente, tramite **OpenSSL** (ciò comporta la presenza di avvertenze specifiche all'interno dei principali browser)
- Sfruttando il servizio gratuito **Let's Encrypt** (che permette la generazione tramite il tool **Certbot**)
- Appoggiandosi ad altri servizi (gratuiti o a pagamento) in grado di fornire certificati firmati da Certification Autorities note 

Al fine di semplificare le attività di testing, lo script shell `proxy/gen-certs` permette, tramite OpenSSL, la generazione dei certificati necessari all'interno della directory `proxy/certificates/`.

## Variabili d'ambiente utilizzate

Al fine di una corretta esecuzione, l'applicativo prevede la presenza delle seguenti variabili ambientali:

| Variabile | Descrizione |
|-----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token utilizzato dalla classe `Bot` al fine di controllare il bot telegram creato |
| `INFLUXDB_API_USER` | Nome utente per connessione ad InfluxDB tramite InfluxDBClient |
| `INFLUXDB_API_PASSWORD` | Password per connessione ad InfluxDB tramite InfluxDBClient |
| `AUTH_USERNAME` | Nome utente del primo utente amministratore, creato automaticamente per Monitoring Tool |
| `AUTH_USERPASS` | Password del primo utente amministratore, creato appositamente per accedere a Monitoring Tool |
| `MOSQUITTO_USERNAME` | Nome utente necessario alla connessione con il servizio di MQTT Brokering |
| `MOSQUITTO_PASSWORD` | Password necessaria alla connessione con il servizio di MQTT Brokering |

\newpage

## Containerizzazione di AirPI 

Come per i servizi precedentemente descritti, anche per AirPI è stata adottata una strategia basata sull'utilizzo di Docker al fine di racchiudere il servizio all'interno di un apposito container. A tal fine, a partire dall'immagine ufficiale **Alpine** è stato prodotto il Dockerfile di seguito riportato.

|
|

```Dockerfile
FROM alpine

RUN apk -U upgrade
RUN apk add --update --no-cache build-base
RUN apk add --update --no-cache libffi-dev openssl-dev
RUN apk add --update --no-cache sqlite
RUN apk add --update --no-cache python3 && ln -sf python3 /usr/bin/python
RUN python3 -m ensurepip
RUN apk add py3-sqlalchemy
RUN pip3 install --no-cache --upgrade pip setuptools
RUN pip3 install --no-cache --upgrade flask
RUN pip3 install --no-cache --upgrade influxdb
RUN pip3 install --no-cache --upgrade flask_sqlalchemy
RUN pip3 install --no-cache --upgrade flask_jwt_extended
RUN pip3 install --no-cache --upgrade Flask-MQTT
RUN pip3 install --no-cache --upgrade passlib
RUN pip3 install --no-cache --upgrade gunicorn

RUN mkdir /app
RUN mkdir /log

WORKDIR /app

COPY ./app /app

```

|
|

Quest'ultimo, in particolare, prevede: 

- L'installazione del package `build-base`, necessario al building di alcune librerie installate nel corso dei passaggi successivi
- L'installazione di **Python**, **pip** e delle librerie necessarie alla corretta esecuzione dell'applicativo
- La creazione delle directory predisposte al contenimento del codice sorgente dell'applicativo e di eventuali file di log
- Il popolamento della cartella `/app` con i file presenti al percorso `airpi/app` della macchina host

\newpage

```python

import sqlite3
from passlib.hash import pbkdf2_sha256
import os
import sys

USERNAME = os.environ['AUTH_USERNAME']
PASSWORD = os.environ['AUTH_USERPASS']
DB = '/app/appdb.db'

conn = sqlite3.connect(DB)
c = conn.cursor()

try:
    c.execute('SELECT name FROM user where name=?', (USERNAME,))

    if not c.fetchone():
        c.execute('
			INSERT INTO user(name, password, is_admin) VALUES (?,?,1)', 
			(USERNAME, pbkdf2_sha256.hash(PASSWORD))
		)
        conn.commit()
except Exception as e:
    conn.rollback()
finally:
    conn.close()

sys.exit(0)

```

Non essendovi un comando espresso tramite l'istruzione `CMD` o `ENTRYPOINT`, è necessario che il container venga eseguito esplicitando i seguenti comandi: 

```bash
python3 first_user.py
gunicorn app:app -w 1 --bind 0.0.0.0:5000
```

Questi ultimi prevedono:

- La creazione del primo utente del database (nel caso in cui quest'ultimo non risulti presente)
- L'esecuzione di AirPI tramite Gunicorn (dove `-w 1`, in particolare, esplicita un numero di workers pari ad uno a fini di compatibilità con Flask MQTT)

|
|

## Containerizzazione di nginx

Il servizio di reverse proxying precedentemente descritto è stato containerizzato come servizio indipendente. A tal fine, l'immagine è stata configurata, a partire da `nginx:mainline-alpine`, tramite il Dockerfile riportato di seguito. 

|
|

```dockerfile
FROM nginx:mainline-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d
RUN mkdir /certificates
COPY ./certificates /certificates
```

|
|

Quest'ultimo permette: 

- L'inclusione di un file di configurazione ad-hoc (con annessa rimozione della configurazione di default)
- L'inclusione dei certificati SSL necessari 

In particolare, il file di configurazione (riportato di seguito) prevede l'istituzione di un web-server in ascolto sulle porte 80 e 443 (via ssl) che:

- Carica i certificati SSL
- Redirige le richieste al rispettivo endpoint del server WSGI di AirPI
- Assicura che le richieste `HTTP` siano redirette ad `HTTPs`

```conf

server {
    listen 443 ssl;


    ssl_certificate /certificates/cert.pem;
    ssl_certificate_key /certificates/key.pem;

	# Change with your hostname
	server_name localhost;


 location / {

           proxy_pass http://airpi:5000/;
		   proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
		   proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

		   # Define the maximum file size on file uploads
		   client_max_body_size 5M;
       }


}

server {
    listen 80;

	# Change with your hostname
    server_name localhost;

    return 302 https://$server_name$request_uri;
}

```

\newpage

# Deployment

## Soluzione adottata per il dispiegamento dei servizi 

Il dispiegamento dei servizi descritti è reso possibile dallo strumento `docker-compose`, che permette la definizione e organizzazione di applicativi multi-container tramite l'apposito file `docker-compose.yaml` consultabile alla root directory della repository. In particolare, la principale soluzione di deployment prevede l'organizzazione di un unico stack multi-container.

## Aspetti di docker-compose coinvolti

All'interno del file `docker-compose`, per ogni servizio vengono specificati:

- **Dockerfile** e **directory di riferimento** per il build della rispettiva immagine
- **Politiche di riavvio** dei container in seguito ad errori
- **Port mapping** (al fine di esporre le porte necessarie all'utilizzo)
- **Volume mapping** (al fine di mappare su volumi persistenti directory interne ai container) 
- **Variabili d'ambiente** necessarie all'esecuzione
- **Nome** dei container
- **Dipendenze fra container** (al fine di permettere un corretto avvio e spegnimento del sistema, oltre che un comportamento consistente dello stack nel caso di errori)

Al fine di agevolare l'eventuale modifica delle variabili d'ambiente necessarie, quest'ultime sono state descritte all'interno di un file `.env` (consultabile all'interno della root directory della repository). Quest'ultimo viene, infatti, automaticamente letto dal file `docker-compose` durante la sua esecuzione.

Il risultato finale viene riportato di seguito:

```docker-compose

version: "3"
services:
  proxy:
    build:
      context: ./proxy
    container_name: proxy
    volumes:
      - ./proxy/certificates:/certificates
    depends_on:
      - "airpi"
    ports:
      - "443:443"
      - "80:80"
    restart: always

  airpi:
    build:
      context: ./airpi
    container_name: airpi 
    stdin_open: true
    tty: true
    command: sh -c "python3 first_user.py; gunicorn app:app -w 1 --bind 0.0.0.0:5000"
    environment:
      - INFLUXDB_API_USER
      - INFLUXDB_API_PASSWORD
      - TELEGRAM_BOT_TOKEN
      - AUTH_USERNAME
      - AUTH_USERPASS
    depends_on:
      - "database"
      - "broker"
    restart: always

  broker:
    build:
      context: ./broker
    environment:
      - MOSQUITTO_USERNAME
      - MOSQUITTO_PASSWORD
    container_name: broker
    ports:
      - "1883:1883"
    volumes:
      - ./broker/log:/mosquitto/log
    restart: always

  database:
    build:
      context: ./influxdb
    container_name: database
    environment:  
      - INFLUXDB_ADMIN_USER
      - INFLUXDB_ADMIN_PASSWORD
    volumes:
      - db:/var/lib/influxdb
    ports:
      - "8086:8086"
    restart: always 

volumes:
  db:

```

Si osserva come il servizio `airpi` non includa alcun port mapping. L'accesso agli endpoint è permesso, infatti, solamente dal reverse proxy, che espone le porte `80` e `443` per connessioni rispettivamente `HTTP` ed `HTTPs`.

## Deployment su Raspberry PI

Al fine di dispiegare la soluzione proposta su una piattaforma low-cost in grado di esporre continuativamente nell'arco delle giornata i servizi implementati, è stato scelto di eseguire il sistema sfruttando una **Raspberry Pi 4B**. 

In particolare, in sostituzione a **Raspbian** è stato installato il sistema operativo **Ubuntu Server 21.04**, nella versione con architettura **ARM64**. In seguito all'installazione è stato necessario: 

1. Eseguire i processi di **update** e **upgrade** rispettivamente tramite i comandi `sudo apt update` e `sudo apt upgrade`
2. Installare `git` tramite il comando `sudo apt install git`
3. Installare docker tramite lo script di convenienza `get-docker.sh`
4. Eseguire il clone della respository tramite il comando `git clone https://github.com/canta2899/vindriktning-iot`
5. Effettuare il build delle immagini Docker tramite l'utility `docker-compose build`
6. Avviare i servizi tramite l'utility `docker-compose up`

Al fine di agevolare la connessione delle unità VINDRIKTNING, alla Raspberry è stato, infine, assegnato un indirizzo ip statico tramite l'applicazione di un'apposita eccezione all'interno del **DHCP** del router locale. 

L'esposizione del servizio **Monitoring Tool** all'esterno della rete locale è reso possibile tramite l'applicazione di un'opportuna configurazione di **port forwarding** nel router locale, con eventuale aggiunta di un DNS **statico** (nel caso in cui l'utilizzo sia reso possibile dal proprio provider) o, in alternativa, **dinamico** tramite servizi quali **DynDNS**, **NoIP** e altri.

Si tiene presente, inoltre, il costo dell'hardware, disponibile online in varie soluzioni a partire da un prezzo di 35€ circa. Integrando, quindi, la tabella dei costi descritta in precedenza si ottiene il seguente risultato:

| Componente | Costo Individuale | Quantità acquistate |
|------------|------------------:|--------------------:|
| VINDRIKTNING |  9,95 €         |     2               |
| D1 Mini    |    4,00 €         |     2               |
| Cavi Dupont|    3,00 €         |     1               |
| Raspberry Pi 4 | 40,00 €		 |     1			   |

Di conseguenza, il costo coinvolto nella personalizzazione di una singola unità VINDRIKTNING e nell'acquisto di hardware dedicato per dispiegare i servizi implementati raggiunge la cifra di **56,95 €**. Tuttavia, la personalizzazione di due unità richiede una spesa complessiva pari a **87,85 €**. Infine, l'utilizzo di modelli più economici di Raspberry Pi e similari permette un notevole abbattimento dei costi.

\newpage

## Rappresentazione grafica dell'architettura finale

In conclusione, la seguente rappresentazione grafica descrive la soluzione architetturata, specificando i servizi coinvolti.

\begin{figure}[H]
\centering
\includegraphics[width=450px]{img/architettura.png}
\end{figure}

\newpage

# Conclusioni

## Guida alla installazione e configurazione del sistema

Al fine di replicare l'integrazione presentata, è sufficiente seguire i passaggi di seguito elencati: 

1. Eseguire il flash del firmware su tutti i dispositivi ESP8266 interessati
2. Installare i dispositivi ESP8266 all'interno delle unità VINDRIKTNING
3. Alimentare i sensori tramite cavo USB di tipo C

Successivamente, è possibile:

1. Connettersi ad ogni unità VINDRIKTNING (esposta come Soft Access Point e osservabile fra le reti disponibili)
2. Specificare tramite l'apposito menu di configurazione:
	- La rete Wi-Fi a cui connettersi
	- La password della rete
	- L'indirizzo IP del Broker MQTT
	- Il nome utente e la password necessari alla connessione al Broker MQTT
	- Il nome proprio del sensore (si consiglia di assegnare ad ogni unità il nome della stanza in cui esse si trovano)

All'interno della macchina adibita al dispiegamento dei servizi necessari diviene, quindi, possibile:

1. L'ottenimento del software tramite il comando `git clone https://github.com/canta2899/vindriktning-iot.git`
2. La generazione e/o l'inserimento dei certificati per HTTPS all'interno della cartella `nginx/certificates` (da creare, se necessario)
3. La creazione di un file `.env` contenente i valori associati alle seguenti variabili: 
	- `MOSQUITTO_USERNAME` (nome utente del Broker MQTT)
	- `MOSQUITTO_PASSWORD` (password del Broker MQTT)
	- `INFLUXDB_ADMIN_USER` (nome dell'utente amministratore del database InfluxDB)
	- `INFLUXDB_ADMIN_PASSWORD` (password dell'utente amministratore del database InfluxDB)
	- `INFLUXDB_API_USER` (nome dell'utente "api" del database InfluxDB)
	- `INFLUXDB_API_PASSWORD` (password dell'utente "api" del database InfluxDB)
	- `TELEGRAM_BOT_TOKEN` (token ottenuto da BotFather in seguito alla creazione del bot Telegram)
	- `AUTH_USERNAME` (nome dell'utente creato al primo avvio del sistema al fine di poter accedere a Monitoring Tool)
	- `AUTH_USERPASS` (password dell'utente creato al primo avvio del sistema al fine di poter accedere a Monitoring Tool)
4. L'eventuale modifica del volume mapping definito in `docker-compose.yaml` in base alle proprie preferenze

Infine, i servizi possono essere eseguiti tramite l'utility

```bash
docker-compose up
```

oppure

```bash
docker-compose up -d 
```

specificando, così, l'avvio in modalità detached al fine di non ottenere in risposta il **log interattivo** fornito da docker-compose.

Lo spegnimento del sistema è permesso, invece, dal comando

```bash
docker-compose stop
```

## Follow ups

Nel corso dello svolgimento dell'attività progettuale sono stati, inoltre, individuati aspetti che permettono un ulteriore raffinamento della soluzione proposta, espandendone le funzionalità. In particolare, sono state individuate le seguenti variazioni e funzionalità:

- Implementazione di un applicativo mobile in sostituzione al Bot Telegram al fine di fornire uno strumento ad-hoc per permettere l'interazione con l'utenza
- Implementazione di appositi moduli integrativi al fine di permettere l'interazione fra VINDRKTNING ed altri accessori domotici fra cui, ad esempio, il purificatore d'aria **FÖRNUFTIG** di Ikea (che consiglia l'abbinamento pur non offrendo una soluzione in grado di interconnettere i due prodotti), la cui accensione può essere automatizzata tramite prese a muro intelligenti.
- L'espansione di AirPI al fine di permettere:
	- Una più variegata gestione delle utenze e dei permessi associati
	- La possibilità di configurare più gruppi di sensori fra loro indipendenti 
	- La possibilità di associare ad ogni sensore un gruppo di utenti diverso,  mantenendo separati i rispettivi flussi di dati 

## Resoconto finale

La realizzazione del progetto esposto individua una specifica attivtà di modifica del prodotto ufficialmente presentato da IKEA proponendo, attraverso l’integrazione di un firmware ad-hoc e l’implementazione delle componenti software necessarie, uno "**Smart Tool**" in grado di rendere altamente fruibili i dati relativi alla qualità dell'aria raccolti da uno o più sensori.

