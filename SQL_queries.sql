create database ACT;

use ACT;

create table math (
id VARCHAR(15) PRIMARY KEY,
topic VARCHAR(30),
month_year VARCHAR(15),
question_number VARCHAR(3),
question_statement VARCHAR(200),
a1 VARCHAR(100),
a2 VARCHAR(100),
a3 VARCHAR(100),
a4 VARCHAR(100),
a5 VARCHAR(100),
pic blob
);

select * from math;

ALTER TABLE math MODIFY question_statement VARCHAR(500);

#insert excel files via MySQL Workbench GUI