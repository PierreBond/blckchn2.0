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