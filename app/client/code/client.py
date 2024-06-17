# SuperFastPython.com
# example of an echo client using streams
import asyncio
import json
from sys import argv


class Client(object):

    def __init__(self, name):
        self.server_address = 'redsoft'
        self.server_port = 9991
        self.name = name
        self.input_user = False
        self.start = 0
        self.COMMANDS = {
            'login': self.login,
            'close': self.close
        }


    async def login(self):
        self.start = True

    async def send_message(self, writer, message):
        # report progress
        print(f'request: {message.strip()}')
        # encode message to bytes
        msg_bytes = message.encode()
        # send the message
        writer.write(msg_bytes)
        # wait for buffer to empty
        await writer.drain()

    async def response(self, reader):
        result_bytes = await reader.readline()
        response = result_bytes.decode()
        response = response.strip()
        return response

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()
        
        #client.send_message(client.writer, 'close'+'\n')
    
    async def open_connect(self):
        
        try:
            while True:
                self.reader, self.writer = await asyncio.open_connection(
                    self.server_address, self.server_port)
                
                print('...')

                if not self.start:
                    data = json.dumps({
                        'client': self.name,
                        'cmd': 'joining'
                    })

                elif self.input_user:
                    a = input('>')
                    data = json.dumps({
                        'client': self.name,
                        'cmd': a
                    })
                else:
                    data = json.dumps({
                        'client': self.name,
                        'cmd': 'keep'
                    })
                
                await self.send_message(self.writer, data+'\n')

                resp = await self.response(self.reader)
                if not resp:
                    print(resp)
                    print('not data')
                    return
                resp = json.loads(resp)
                
                if resp['cmd'] in self.COMMANDS:
                    await self.COMMANDS[resp['cmd']]()
                    if not self.start:
                        return
                    

                print('response', resp)
                self.start = True

                self.writer.close()
                await self.writer.wait_closed()
                

        except asyncio.CancelledError as ex:
            self.reader, self.writer = await asyncio.open_connection(
                self.server_address, self.server_port)

            data = json.dumps({
                        'client': self.name,
                        'cmd': 'close'
            })

            await self.send_message(self.writer, data+'\n')
            self.writer.close()
            await self.writer.wait_closed()
            #print('task1>>>>', type(ex))
            raise





            
       
 


# run the event loop
script, name = argv
client = Client(name)

try:
    asyncio.run(client.open_connect())
except KeyboardInterrupt:
    print('quit')


# from sys import argv

# print(name)