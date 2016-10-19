CREATE TABLE "moves" ("mid" INTEGER PRIMARY KEY  NOT NULL , "uid" INTEGER NOT NULL , "sid" INTEGER NOT NULL , "move" TEXT NOT NULL , "ts" TEXT NOT NULL );
CREATE TABLE "session_types" ("sid" INTEGER PRIMARY KEY  NOT NULL  UNIQUE , "params" TEXT, "info" TEXT);
CREATE TABLE "sessions" ("sid" INTEGER PRIMARY KEY  NOT NULL  UNIQUE , "uid" INTEGER, "type" INTEGER, "start" TEXT, "end" TEXT);
CREATE TABLE "users" ("uid" INTEGER, "username" TEXT NOT NULL , PRIMARY KEY ("uid", "username"));
