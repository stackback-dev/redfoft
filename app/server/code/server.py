# # SuperFastPython.com
# # example of an echo server using streams
import asyncio, json, logging, asyncpg, inspect
import crypt
from hmac import compare_digest as compare_hash

logging.basicConfig(level=logging.INFO, filename="server.log", filemode="w")

class obj(object):
    def __init__(self, d):
        for k, v in d.items():
            if isinstance(k, (list, tuple)):
                setattr(self, k, [obj(x) if isinstance(x, dict) else x for x in v])
            else:
                setattr(self, k, obj(v) if isinstance(v, dict) else v)
    
    def __str__(self):
        return f'Machinery'



class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.connect(
            user='admin',
            password='12345',
            database='storage',
            host='postgres',
            port='5432',
        )

class Machinery:
    db = Database()

    @classmethod
    async def create(self, data):
     
        await self.db.connect()
        machinery_id = await self.db.pool.fetchval('''
            INSERT INTO machinery (name, ram, cpu, pswd) VALUES
                ($1, $2, $3, crypt($4, gen_salt('md5')))
            RETURNING id;
        ''', data['name'], int(data['ram']), int(data['cpu']), data['pswd'])
        
        disklist = []
        for disk in data['disk']:
            disk_id = await self.db.pool.fetchval('''
                INSERT INTO disk (volume) VALUES
                    ($1)
                RETURNING id;
            ''', int(disk))
            
            disklist.append((machinery_id, disk_id, ))
        
        
        await self.db.pool.executemany(
            'INSERT INTO machinery_disk (machinery_id, disk_id) VALUES ($1, $2)',
            disklist
        )

    
    async def connect(self):
        await self.db.connect()
        
    @classmethod
    async def all_disk(self):
        await self.db.connect()
        print('all_disk')
        query = inspect.cleandoc(f'''
            SELECT 
                machinery.*, 
                disk.*
            FROM machinery_disk
            JOIN machinery ON machinery.id = machinery_disk.machinery_id 
            JOIN disk ON disk.id = machinery_disk.disk_id             
            '''
        )
        rows = await self.db.pool.fetch(query)
        for row in rows:
            print(dict(row))
        

    
    @classmethod
    async def update(self, client, data):
        parse = data.split(':')
        field = parse[0]
        value = parse[1]
        pk = client['db'].id
        print(field, value)
        await self.db.pool.fetch(f'''
                UPDATE machinery
                SET {field} = '{value}'
                WHERE id = '{pk}';                         
            ''')
    
    
    @classmethod
    async def is_used(self):
        await self.db.connect()
        query = inspect.cleandoc(f'''
            SELECT machinery.*, json_agg (json_build_object('id', disk.id, 'volume', disk.volume )) AS disk
            FROM machinery
            LEFT OUTER JOIN machinery_disk
            ON machinery.id = machinery_disk.machinery_id
            LEFT OUTER JOIN disk
            ON machinery_disk.disk_id = disk.id
            where machinery.used = true
            GROUP BY machinery.id
            '''
        )
        rows = await self.db.pool.fetch(query)
        if rows:
            for row in rows:
                print(dict(row))
        return

    
    async def get_object(self, **kwargs):
        name = kwargs['client']
        query = inspect.cleandoc(f'''
            SELECT machinery.*, json_agg (json_build_object('id', disk.id, 'volume', disk.volume )) AS disk
            FROM machinery
            LEFT OUTER JOIN machinery_disk
            ON machinery.id = machinery_disk.machinery_id
            LEFT OUTER JOIN disk
            ON machinery_disk.disk_id = disk.id
            where machinery.name = '{name}'
            GROUP BY machinery.id
            LIMIT 1
            '''
        )

       
        rows = await self.db.pool.fetch(query)
        if rows:
            await self.db.pool.fetch(f'''
                UPDATE machinery
                SET used = true
                WHERE name = '{name}';                         
            ''')
            return obj([dict(row) for row in rows][0]) 
        
        return

      



class Server(object):
    host = 'redsoft'
    port = 9991
    clients = {}
    data = {}

    def __init__(self):
        self.commands = {
            'online': self.online,
            'login': self.login,
            'joining': self.joining,
            'create': self.create,
            'auth': self.auth,
            'used': self.used,
            'logout': self.logout,
            'update': self.update,
            'devices': self.devices,
            'close': self.close
        }
        
        asyncio.run(self.main())
        
    
    async def close(self):
        print(self.client)
    
    async def devices(self):
        await Machinery.all_disk()
    
    async def update(self):
        await Machinery.update(self.client, self.value)
    
    async def logout(self):
        self.clients[self.client['db'].name]['db'].auth = False
        print('goodbye', self.client['db'].name)

    async def used(self):
        await Machinery.is_used()
    
    
    async def auth(self):
        clients = filter(lambda key: key if hasattr(self.clients[key]['db'] , 'auth') and self.clients[key]['db'].auth == True else None, self.clients.keys())
        clients = list(clients)
     
        for client in clients:
            line = '> [{}] {}'.format(
                client,
                self.clients[client]['db'].__dict__

            )
            print(line)


    
    async def online(self):
        for client in self.clients:
            line = '> [{}] {}'.format(
                client,
                self.clients[client]['db'].__dict__

            )
            print(line)


    async def joining(self):
        vm = Machinery()
        await vm.connect()
        self.vm = await vm.get_object(**self.data)
        self.vm.auth = False
        
        if not self.vm:
            self.data['cmd'] = 'close'
            await self.send(self.clients[self.data['client']]['link'], self.data)
            del self.clients[self.data['client']]
            return
        self.clients[str(self.vm.name)]['db'] = self.vm
        
        
    
    async def login(self):
        parse = self.value.split('@')
        user = parse[0]
        pwd = parse[1]
        hash_ = self.client['db'].pswd
        success = compare_hash(crypt.crypt(pwd, hash_), hash_)
        self.clients[user]['db'].auth = success
        if success:
            await self.send(self.clients[user]['link'], {
                'cmd': 'auth',

            })

    
    async def create(self):
        fields = {}
        for field in ['name', 'ram', 'cpu', 'pswd', 'disk']:
            c  = input(field+': ')
            fields[field] = c
            if field != 'disk':
                fields[field] = c
            else:
                fields[field] = [c]
        n = 1
        
        while True:
            print('press "c" exit add disk')
            c  = input('disk (MB) '+str(n)+': ')
            if c == 'c':
                await Machinery.create(fields)
                return
            
            fields['disk'].append(c)
            n += 1
        
        
    
    
    async def ainput(self, prompt):
        loop = asyncio.get_event_loop()
        # Ждём действия от пользователя
        while True:
            # Запускаем input() в отдельном потоке и ждём его завершения
            return await loop.run_in_executor(None, input, prompt)


    async def send(self, writer, msg):
        msg = json.dumps(msg)
        writer.write(msg.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        print('Closing connection')


    async def handle_echo_client(self, reader, writer):

   
        msg_bytes = await reader.readline()
        data = msg_bytes.decode().strip()
        self.data = json.loads(data)
        
   
        if self.data['cmd'] == 'close':
            print(self.data)
            # close the connection
            writer.close()
            await writer.wait_closed()
            del self.clients[self.data['client']]
            # report progress
            print('goodbye')
            return
        
        
        if self.data['cmd'] == 'keep':
            self.clients[self.data['client']]['link'] = writer
            return
        
        self.clients[self.data['client']] = {
            'db': None,
            'link': writer
        }
        

        if self.data['cmd'] not in self.commands:
            print('[not command]')
            return
        
        await self.commands[self.data['cmd']]()
            
        

        

        #print(asyncio.current_task().get_name(), msg)
        #print(asyncio.get_event_loop()._selector.__dict__)

        return
        
  
 
    async def main(self):
        server = await asyncio.start_server(self.handle_echo_client, self.host, self.port)
        # run the server
        async with server:
            # report message
            print('Server running...')
            while True:
                cmdinput = await self.ainput('>>>')
                cmdlist = cmdinput.split(' ')
                if len(cmdlist) < 3:
                    for add in range(3 - len(cmdlist)):
                        cmdlist.append(None)

                self.cmd, client, self.value = tuple(cmdlist)
                if client:
                    if client in self.clients:
                        self.client = self.clients[client]
                    else:
                        print('[client offline]')
                        continue


                
                if self.cmd not in self.commands:
                    print('[not command]')
                    continue
                
                    
                await self.commands[self.cmd]()
                
             

                # elif self.clients.get(client, False):
                #     await self.send(clients[client], data)
                # else:
                
                #print('error', clients.keys())
        
                #accept connections
            await server.serve_forever()
 
server = Server()
# start the event loop






###
# python 3.7+
# import socket
# import asyncio

# class SocketHandler():
#     def __init__(self, conn):
#         self.conn = conn
#         self.run_loop = False

#     async def recv_loop(self):
#         try:
#             print('client connected')
#             while True:
#                 cmd = self.conn.recv(1024)  # receive data from client
#                 cmd = cmd.decode()
#                 print(cmd)
#                 task2 = asyncio.create_task(self.whileLoop())
#                 task3 = asyncio.create_task(test_counter())
#                 sock.sendall(b'endLoop')
#                 await task2
#                 await task3
                
                
#                 if len(cmd) == 0:
#                     break
#                 elif cmd == "startLoop":
#                     print(25)
#                     self.run_loop = True
#                     task2 = asyncio.create_task(self.whileLoop())
#                     task3 = asyncio.create_task(test_counter())
#                     await task2
#                     await task3
#                 elif cmd == "endLoop":
#                     self.run_loop = False
#         finally:
#             self.conn.close()

#     async def whileLoop(self):
#         count = 0
#         while self.run_loop:
#             print('self.run_loop: ' + str(self.run_loop))
#             # the below line should allow for other processes to run however
#             # 'cmd = self.conn.recv(1024)' only runs after the while loop breaks
#             await asyncio.sleep(1)

#             # break the loop manually after 5 seconds
#             count += 1
#             if count > 5:
#                 break

# async def test_counter():
# # just a dummy async function to see if the whileLoop func
# # allows other programs to run
#     for k in range(5):
#         print(str(k))
#         await asyncio.sleep(1)

# async def main():
#     # this is the main asyncio loop that initializes the socket
#     sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
#     # sock.setblocking(False)

#     # Bind the socket to the address given on the command line
#     server_address = ("127.0.0.1", 9991)
#     print('starting up on %s port %s' % server_address)
#     sock.bind(server_address)
#     sock.listen(1)
#     while True:
#         print('waiting for a connection')
#         connection, client_address = sock.accept()
#         socketHandler = SocketHandler(connection)
#         task1 = asyncio.create_task(socketHandler.recv_loop())  # create recv_loop as a new asyncio task
#         await task1

# if __name__ == '__main__':
#     asyncio.run(main())