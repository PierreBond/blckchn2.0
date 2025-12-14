Below are the **exact minimal steps** you just ran ,copy/paste or save them as a checklist.  



1. Activate venv

powershell
cd C:\YourComputer\blckchn2.0
.\.venv\Scripts\Activate

prompt becomes (.venv) PS C:\YourComputer\blckchn2.0>

2. Start the node

powershell
python blckchn.py

leave this window open.


3. Mine a block (new PowerShell tab)

(powershell)
curl.exe -s http://localhost:5000/mine

you get the JSON with `"message":"New Block Forged"` and the block data.


4. Send a coin transaction

(powershell)
$url  = "http://localhost:5000/transactions/new"
$body = @{sender="you"; recipient="friend"; amount=10} | ConvertTo-Json
Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"

 response:

message

Transaction will be added to Block 4



5. View the full chain any time


powershell
curl.exe -s http://localhost:5000/chain | jq

(if you don’t have `jq` just omit it for raw JSON)



6. Stop everything

- Ctrl-C in the terminal window running `python blckchn.py`  
- `deactivate` (optional) to leave the venv

That’s the whole loop: start -> mine -> send tx -> inspect -> stop.


7. Node Network Formation

- in a two separate terminal , run python blckchn.py -p 5001 and python blckchn.py -p 5002 respectively.

- we run this command to register the two neighbours irm -Uri http://localhost:5000/nodes/register -Method Post `
>>     -ContentType "application/json" `
>>     -Body '{"nodes":["192.168.0.108:5001","192.168.0.108:5002"]}'

- expected response should be 
message                    total_nodes
-------                    -----------
New  nodes have been added {192.168.0.108:5001, 192.168.0.108... 

- run consensus with this code 
(irm -Uri http://localhost:5000/nodes/resolve -Method Get).message

- expected response should be 
Our chain was authoritative or Our chain was replaced 
(first one means your miner in the primary port ie 5000 is the longest, replaced meaning one of the other node had more blocks)

- equality check is done using this command 
5000..5002 | % { (irm "http://192.168.0.108:$_/chain").length } and the expected output is or should look like this 
2
1
1
