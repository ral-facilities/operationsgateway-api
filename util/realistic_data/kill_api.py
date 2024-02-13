from time import sleep
from util.realistic_data.ingest.api_starter import APIStarter

print("About to start API")
starter = APIStarter()
print("Just started API, going to sleep")
sleep(5)
print("Sleep finished, kill process")
starter.kill()
print("Process killed")
