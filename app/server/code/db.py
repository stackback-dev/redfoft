import asyncio
import asyncpg
import datetime


async def insert_many(conn, data):
    await conn.executemany(
        'INSERT INTO machinery_disk (machinery_id, disk_id) VALUES ($1, $2)',
        data
    )



async def main():
    # Establish a connection to an existing database named "test"
    # as a "postgres" user.
    conn = await asyncpg.connect(
        user='admin',
        password='12345',
        database='storage',
        host='postgres',
        port='5432',
    )
    
    # await conn.execute('''
    #     DROP TABLE machinery, disk, machinery_disk
    # ''')
    # return
    
    
    
    # Execute a statement to create a new table.
    
    
    await conn.execute('''
        CREATE TABLE machinery(
            id serial PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            ram INT NOT NULL,
            cpu INT NOT NULL,
            pswd VARCHAR(100) NOT NULL,
            used BOOLEAN DEFAULT false
        )
    ''')

    
    await conn.execute('''
        CREATE TABLE disk(
            id serial PRIMARY KEY,
            volume INT NOT NULL
        )
    ''')
    
    await conn.execute('''
        CREATE TABLE machinery_disk
        (
            machinery_id INTEGER NOT NULL REFERENCES machinery,
            disk_id   INTEGER NOT NULL REFERENCES disk,
            UNIQUE (machinery_id, disk_id)
        )
    ''')
    
    
    await conn.execute('''
        INSERT INTO disk (volume) VALUES
            ('20000'),
            ('40000'),
            ('80000')
        RETURNING id;
    ''')

    await conn.execute('''
        INSERT INTO machinery (name, ram, cpu, pswd) VALUES
            ('admin', '4000', '2', crypt('admin', gen_salt('md5'))),
            ('manager', '6000', '4', crypt('manager', gen_salt('md5')))
        RETURNING id;
    ''')

    await insert_many(conn, [(1, 1), (1, 2), (2, 3)])

    # Insert a record into the created table.
    # await conn.execute('''
    #     INSERT INTO users(name, dob) VALUES($1, $2)
    # ''', 'Bob', datetime.date(1984, 3, 1))

    # # Select a row from the table.
    # row = await conn.fetchrow(
    #     'SELECT * FROM users WHERE name = $1', 'Bob')
    # *row* now contains
    # asyncpg.Record(id=1, name='Bob', dob=datetime.date(1984, 3, 1))

    # Close the connection.
    await conn.close()

async def select():
    
    conn = await asyncpg.connect(
        user='admin',
        password='12345',
        database='storage',
        host='postgres',
        port='5432',
    )
    rows = await conn.fetch('''
        SELECT machinery.*, json_agg(json_build_object('id', disk.id)) AS disk
        FROM machinery
        LEFT OUTER JOIN machinery_disk
        ON machinery.id = machinery_disk.machinery_id
        LEFT OUTER JOIN disk
        ON machinery_disk.disk_id = disk.id
        GROUP BY machinery.id
        ''')
    for item in [dict(row) for row in rows]:
        print(item)



asyncio.get_event_loop().run_until_complete(main())