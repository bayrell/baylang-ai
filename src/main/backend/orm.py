from helper import Index, get_current_datetime, get_datetime_from_utc
from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    
    model_config = ConfigDict(validate_assignment=True)
    _updated: set = set()
    _old_pk: dict = {}
    
    @classmethod
    def table_name(cls):
        return ""
    
    @classmethod
    def autoincrement(cls):
        return False
    
    @classmethod
    def primary_key(cls):
        return []
    
    @classmethod
    def has_updated_datetime(cls):
        return False
    
    @classmethod
    def add_foreign_items(cls, items, key, foreign, foreign_key):
        
        """
        Add foreign_item to each item[key]
        """
        
        index = Index(items)
        for foreign_item in foreign:
            item = index.get(foreign_item[foreign_key])
            item[key].append(foreign_item)
    
    
    @classmethod
    def get_primary_list_from_data(cls, data):
        if isinstance(data, list):
            return data
        
        if isinstance(data, dict):
            pk = cls.primary_key()
            item = [data[key] if key in data else None for key in pk]
            return item
        
        return [data]
    
    
    @classmethod
    async def get_by_id(cls, database, id, fields=["*"]):
        
        """
        Get chat by id
        """
        
        # Get where
        pk = cls.primary_key()
        where = [database.escape_field(key) + "=%s" for key in pk]
        args = cls.get_primary_list_from_data(id)
        
        # Query to database
        table_name = cls.table_name()
        item = await database.fetch(f"""
            select {database.join_fields(fields)} from {table_name} where {",".join(where)}
        """, args)
        
        return cls.from_database(item)
    
    
    @classmethod
    async def load_all(cls, database, fields=["*"]):
        
        """
        Load all items
        """
        
        table_name = cls.table_name()
        items = await database.fetchall(f"""
            SELECT {database.join_fields(fields)}
            FROM {table_name}
        """)
        items = [cls.from_database(item) for item in items]
        return items
    
    
    @classmethod
    async def delete(cls, database, id):
        
        """
        Delete chat by id
        """
        
        # Get where
        pk = cls.primary_key()
        where = [database.escape_field(key) + "=%s" for key in pk]
        args = cls.get_primary_list_from_data(id)
        
        # Query to database
        table_name = cls.table_name()
        await database.execute(f"delete from {table_name} where " + ",".join(where), args)
    
    
    async def create(self, database):
        
        """
        Create object
        """
        
        # Add updated datetime
        gmtime_now = get_current_datetime()
        if self.has_updated_datetime():
            if self.gmtime_created is None:
                self.gmtime_created = gmtime_now
            if self.gmtime_updated is None:
                self.gmtime_updated = gmtime_now
        
        # Convert item
        item = self.to_database(self)
        table_name = self.table_name()
        
        # Remove primary key
        if self.autoincrement():
            pk = self.primary_key()
            for key in pk:
                if key in item:
                    del item[key]
        
        keys = item.keys()
        fields = [database.escape_field(key) for key in keys]
        values = ["%s"] * len(keys)
        args = [item[key] for key in keys]
        query = f"""
            INSERT INTO {table_name} ({",".join(fields)})
            VALUES ({",".join(values)})
            """
        
        result = await database.insert(query, args)
        
        if self.autoincrement():
            pk = self.primary_key()
            if len(pk) == 1:
                key = pk[0]
                if not key in item:
                    setattr(self, key, result)
        
        self._updated = set()
        self._old_pk = self.get_primary_key()
    
    
    async def update(self, database):
        
        """
        Update to database
        """
        
        # Add updated datetime
        gmtime_now = get_current_datetime()
        if self.has_updated_datetime():
            if self.gmtime_updated is None:
                self.gmtime_updated = gmtime_now
        
        # Convert item
        item = self.to_database(self)
        table_name = self.table_name()
        
        # Get updated fields
        updated = self.updated()
        if len(updated) == 0:
            return
        values = [database.escape_field(key) + "=%s" for key in updated]
        
        pk_keys = self._old_pk.keys()
        pk_values = [database.escape_field(key) + "=%s" for key in pk_keys]
        
        args = [item[key] if key in item else None for key in updated]
        args.extend([self._old_pk[key] for key in pk_keys])
        query = f"""
            UPDATE {table_name}
            SET {",".join(values)}
            WHERE {",".join(pk_values)}
            """
        
        await database.execute(query, args)
        
        self._updated = set()
        self._old_pk = self.get_primary_key()
        
    
    async def save(self, database):
        
        """
        Save to database
        """
        
        if self.is_create():
            await self.create(database)
        
        else:
            await self.update(database)

    
    def get_primary_key(self, data=None):
        
        """
        Returns primary key
        """
        
        if data is None:
            data = self
        
        pk = self.primary_key()
        item = {}
        for key in pk:
            item[key] = data[key] if key in data else None
        return item
    
    
    def is_create(self):
        
        """
        Returns true if model should be create
        """
        
        pk = self.primary_key()
        id = self._old_pk.get(pk[0])
        return id is None or id == 0
    
    
    def is_update(self):
        
        """
        Returns true if model should be update
        """
        
        pk = self.primary_key()
        id = self._old_pk.get(pk[0])
        return id > 0
    
    
    def updated(self):
        
        """
        Returns updated fields
        """
        
        return list(self._updated)
    
    
    def set_updated(self, key):
        self._updated.add(key)
    
    
    def __init__(self, **data):
        BaseModel.__init__(self, **data)
        self._old_pk = self.get_primary_key(data)
    
    
    def __contains__(self, key):
        return key in self.__annotations__
    
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    
    def __setattr__(self, key, value):
        if key in self.model_fields:
            self._updated.add(key)
        return super().__setattr__(key, value)