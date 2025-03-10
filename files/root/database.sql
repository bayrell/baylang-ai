CREATE TABLE chats (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "gmtime_created" numeric NOT NULL,
    "gmtime_updated" numeric NOT NULL
);

CREATE TABLE messages (
    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
    "chat_id" INTEGER NOT NULL,
    "sender" TEXT NOT NULL,
    "text" TEXT NOT NULL,
    "gmtime_created" numeric NOT NULL,
    "gmtime_updated" numeric NOT NULL,
    FOREIGN KEY (chat_id) REFERENCES chats (id) ON DELETE CASCADE
);