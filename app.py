import webview
import threading
import os

def start_server():
    # Run Django development server
    os.system("python manage.py runserver")

if __name__ == "__main__":
    # Start Django server in a separate thread
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    # Open your Django app in PyWebview
    
    webview.create_window(
     title="Rentaly - Premium Car Rental",   
     url="http://127.0.0.1:8000",         
     width=1200,                            
     height=800,                            
     resizable=True,                        
     fullscreen=True,                       
     icon="icon.png"                       
    )
    webview.start()
