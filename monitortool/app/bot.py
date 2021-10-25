import time
import threading
import requests as r
from requests.exceptions import HTTPError, ConnectionError, Timeout
import queue

"""
                                                                  
                  TELEGRAM BOT IMPLEMENTATION                     
                  ===========================                     
                                                                  
        The following class aims to provide the essentials        
        bot functionalities needed for the purpose of this        
        project without having to rely on external libs and       
                having to conform to their logic.                 
                                                                  
                                                                  
    RUNNING THE BOT                                               
    ===============                                               
                                                                  
    The bot can be instantiated with                              
                                                                  
            b = Bot(YOUR_TOKEN)                                   
                                                                  
    And will start working after                                  
                                                                  
            b.run()                                               
                                                                             
                                                                  
    CALLBACK FUNCTIONS                                            
    ==================                                            
                                                                  
    Callbacks functions can be defined with                       
                                                                  
            b.on(message, callback_function)                      
                                                                  
    The callback function must respect the following definition   
                                                                  
            def callback_function(chat_id, username, params)        
                # your logic                                      

      where                                                       
         - [params] is a list of message words splitted by " "    
         - [chat_id] is the chat id of the sender                 
         - [answer] is a callback function which can be           
           used to reply to the sender                            

    If your bot has to respond your callback can run:

            def callback_function(chat_id, username, params)        
                # your logic                                      
                b.push_notification("message", [chat_id])

    The callback function is not thread safe and may cause race
    conditions if implemented in the wrong way.
                                                                  
                                                                  
    PUSHING GLOBAL NOTIFICATIONS                                  
    ============================                                  
                                                                  
    The method                                                    
                                                                  
            b.push_notification(message, chat_ids)                           
                                                                  
    allows to push a notification message which will be sent      
    to the list of chat_ids provided as the second parameter     
                                                                  
                                                                  
    STOPPING THE BOT                                              
    ================                                               
                                                                  
    In order to stop the bot you can run bot.stop(). The call     
    is blocking and might take some seconds in order to stop      
    the bot properly                                              
                                                                  

"""

class Bot:

    def __init__(self, token):
        
        self.TOKEN = token
        self.offset = 0
        self.timeout = 10
        self.polling_lock = threading.Lock()
        self.polling = True
        self.callbacks = dict()
        self.running_thread = None
        self.q = queue.Queue()
        self.max_retries = 30
        self.s = r.Session()
        self.apisession = r.Session()
        self.token = ''

    
    def push_notification(self, msg, whitelist):

        """
            Pushes notifications to the queue
            which is consumed by the polling
            thread
        """

        self.q.put({'msg': msg, 'whitelist': whitelist})
    

    def __get_next(self):

        """
            Helper function for __send_notification
            which gets the next element in the queue
            marking it as processed. If the queue
            is empty returns None, otherwise returns
            the message to be sent
        """

        try:
            msg = self.q.get_nowait()
            self.q.task_done()
            return msg
        except queue.Empty:
            return None


    def __send_notifications(self):
        
        """
            Sends every notification in the queue
        """

        msg = ""

        while msg is not None:
            msg = self.__get_next()
            if msg is not None:
                self.__sendall(msg['msg'], msg['whitelist'])

        # logging.debug("All notifications sent")


    def on(self, msg, callback):

        """
            Binds the given callback function to
            the message
        """

        self.callbacks[msg] = callback 


    def __send(self, msg, chat_id):

        """
            Sends a message to the given chat_id
        """

        self.s.post(
            f"https://api.telegram.org/bot{self.TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": msg
            }
        )


    def __sendall(self, msg, whitelist):

        """
            Sends a message to all the chat_ids 
        """

        for chatid in whitelist:
            self.__send(msg, int(chatid))

    
    def __parse_msg(self, msg):

        """
            Parses an incoming message by:
                
                - retrieving chatid, msg, user
                - splitting message by ' '
                - searching for a binded callback
                - responding if the user is validated by
                  the logapp endpoint
        """

        # Extracting chat_id, splitting message by whitespaces
        try:
            chat_id = msg['message']['chat']['id']
            mlist = (msg['message']['text']).split(" ")
            username = msg['message']['chat']['username']
        except Exception as e:
            return
        
        # Checking for a callback and performing validation
        if mlist[0] in self.callbacks.keys():
            try:
                self.callbacks[mlist[0]](
                        chat_id, 
                        username,
                        mlist
                )
            except Exception as e:
                return 
     

    def __get_updates(self):
        
        """
            Requests for updates on endpoint, then checks validity. 
            A block of updates is then parsed for each message

            Long polling caused connection problems and the with 
            the bot stopping to respond after a few hours of activity. 

            After intensive debugging it was clear that the polling
            thread was stuck on the POST request below (getUpdates
            endpoint). In order to prevent this issue, an internal
            timeout is set and exceptions are handled by reopening
            a new session in order to re-initiate the connection
        """

        try:

            up =  self.s.post(
                f"https://api.telegram.org/bot{self.TOKEN}/getUpdates",
                data = {
                    "offset": self.offset,
                    "timeout": 15
                },
                timeout=20
            ).json()

        except ValueError as e:
            return

        except (HTTPError, ConnectionError, Timeout) as e:
            self.s = r.Session()
            return

        except Exception as e:
            self.s = r.Session()
            return

        if not up['ok'] or not up['result']: 
            return

        # Parsing every update
        # https://core.telegram.org/bots/api#getupdates

        _ofst = 0

        for msg in up['result']:
            self.__parse_msg(msg)
            _ofst = msg['update_id'] + 1
        self.offset = _ofst


    def __check_polling(self):
        status = True
        with self.polling_lock:
            status = self.polling 
        return status
        

    def __run(self):

        """
            Runs the telegram bot long polling for updates. 
            If the polling causes exceptions MAX_RETRIES times
            in a row then the polling stops. 

            After each polling, enqueued notifications are sent
        """

        while self.__check_polling():
            try:
                self.__get_updates()
                self.__send_notifications()
            finally:
                time.sleep(0.2)  # Sleeps 200 ms before next round


    def stop(self):

        """
            Stops the bot correctly
        """
       
        # Waits for the queue to join
        self.q.join()

        # Sets polling to false in order to stop
        with self.polling_lock:
            self.polling = False

        # joins the polling thread
        self.running_thread.join()


    def run(self):
        
        """
            Runs the bot in a separate thread
        """

        self.running_thread = threading.Thread(
            target=self.__run, 
            args=()
        )
        self.running_thread.start() 

# End Bot Class