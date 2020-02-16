from pymemcache.client.base import Client as Memcached_Cient
import subprocess 

subprocess.Popen("memcached.exe start")

client = Memcached_Cient(('localhost', 11211))
client.set('some_key', "testing1!!!")
result = client.get('some_key')
print(result)