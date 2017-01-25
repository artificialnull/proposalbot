#!/usr/bin/python3

import requests
import json
import os
import time
import random

#telegram bot stuff
url = "https://api.telegram.org/bot%s/%s"
token = open("token.txt").read().replace('\n', '')
print(url % (token, "getUpdates"))

#parameters
publicHelp = """
`/propose [text]` - start a proposal
`/unpropose [id]` - end a proposal
`/help          ` - show this message
additional commands available in private message
"""

privateHelp = """
`/proposals` - list proposals
`/yea [id] ` - agree
`/nay [id] ` - disagree
additional commands available in public message
"""

#requests stuff
ConnectionError = requests.exceptions.ConnectionError

def getUpdates(offset):
    #gets all updates starting with offset
    try:
        r = requests.get(url % (token, "getUpdates"), data={"offset": offset}, timeout=2)
    except:
        print("Error while getting updates")
        return [], offset, True
    try:
        r = json.loads(r.text)
    except:
        return [], offset, True
    r = r["result"]
    if len(r) > 0:
        offset = int(r[-1]['update_id']) + 1
    return r, offset, False

latestOffset = 1
#update current offset to show the latest messages because telegram is dumb
print("Updating...", end="")
oldLatestOffset = 0
while oldLatestOffset < latestOffset:
    oldLatestOffset = latestOffset
    DRAIN, latestOffset, err = getUpdates(latestOffset)
print("\rUpdated    ")

def sendMessage(message, reply_to_message_id=False, tries=0):
    #send message to current chat with content message
    if tries > 3:
        return True
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    if tries > 0:
        #don't parse if we failed the send before
        del payload["parse_mode"]
    if reply_to_message_id:
        #do a reply if specified
        payload['reply_to_message_id'] = reply_to_message_id
        del payload["parse_mode"]
    try:
        tresponse = requests.post(url % (token, "sendMessage"), data=payload, timeout=2)
    except:
        #handle a timeout by trying again with all the same params
        print("Error while sending message (tries: %s)" % str(tries + 1))
        time.sleep(0.5)
        sendMessage(message, reply_to_message_id, tries + 1)
        return True
    try:
        resp = json.loads(tresponse.text)
    except:
        return True
    if not resp["ok"] and tries < 3:
        #something probably went wrong with the parsing, let's try again
        sendMessage(message, reply_to_message_id, tries + 1)
    return False

def loadVotes():
    #puts saved aliases into an aliases dict
    votes = {}
    ids = []
    voteFile = open(path + "/votes.txt").read()
    votes = json.loads(voteFile)
    ids = list(votes.keys())
    return votes, ids

def saveVotes(votes):
    #puts an aliases dict into a savefile
    voteFile = open(path + "/votes.txt", "w")
    voteFile.write(json.dumps(votes, indent=4))
    voteFile.close()

def genID():
    ID = ""
    for x in range(0, 6):
        ID += chr(random.randint(97, 122))
    return ID

path = os.path.dirname(__file__)
chat_id = 0
try:
    votes, ids = loadVotes()
except:
    print("Couldn't load votes, falling back to empty...")
    votes = {}
print("Started")

while True:
    try:
        #reload locked aliases on every cycle
        voters = []
        vfile = open(path + "/voters.txt").read()
        for line in vfile.split('\n'):
            if line != '':
                voters.append(line)

        #get updates and the newest offset
        r, latestOffset, err = getUpdates(latestOffset)

        if len(r) != 0 and not err:
            print("received updates")
        elif err:
            time.sleep(1)

        saveVotes(votes)

        for update in r:
            #loop through each update
            if "message" in update.keys():
                message = update['message']
                chat = message['chat']
                chat_id = chat['id']
                if "from" in message.keys():
                    #find and store name of user
                    user = message['from']
                    if str(user['id']) not in voters:
                        continue
                if chat['type'] in ("group", "supergroup"):
                    print("recv public message")
                    if "text" in message.keys():
                        #get the text of the message
                        text = message['text']
                        if "/propose" == text[:8]:
                            #check if the message is an /alias command and parse
                            if len(votes.keys()) > 5:
                                sendMessage("Too many proposals open for government to be effective")
                            else:
                                content = text[9:]
                                voteID = genID()
                                while voteID in votes.keys():
                                    voteID = genID()
                                votes[voteID] = {'text': content, 'voters': {}}
                                sendMessage("Started proposal with id: " + voteID + "\nPM @proposal_bot to vote")
                        elif "/unpropose" == text[:10]:
                            content = text[11:]
                            if content in votes.keys():
                                del votes[content]
                                sendMessage("Closed proposal")
                        elif "/status" == text[:7]:
                            content = text[8:]
                            if content in votes.keys():
                                voting = 0
                                for vote in votes[content]['voters'].values():
                                    voting += vote
                                sendMessage(content + " stands at " + str(voting))
                        elif "/help" == text[:5]:
                            sendMessage(publicHelp)

                elif chat['type'] == "private":
                    print("recv private message")
                    if "text" in message.keys():
                        text = message['text']
                        if "/proposals" == text[:10]:
                            propstr = ""
                            for key in votes.keys():
                                propstr += '`' + key + "`: " + votes[key]['text'] + '\n'
                            sendMessage(propstr)
                        elif "/yea" == text[:4]:
                            content = text[5:]
                            if content in votes.keys():
                                votes[content]['voters'][str(user['id'])] = 1
                                sendMessage("Your vote has been cast")
                        elif "/nay" == text[:4]:
                            content = text[5:]
                            if content in votes.keys():
                                votes[content]['voters'][str(user['id'])] = -1
                                sendMessage("Your vote has been cast")
                        elif "/setstatus" == text[:10]:
                            content = text[11:]
                            try:
                                vid, val = content.split()
                                val = int(val)
                                voting = 0
                                for vote in votes[vid]['voters'].values():
                                    voting += vote
                                votes[vid]['voters']['offset'] = val - voting
                            except:
                                pass
                        elif "/help" == text[:5] or "/start" == text[:6]:
                            sendMessage(privateHelp)

    except ConnectionError:
        print("ConnectionError") #should put stuff here but whatever
    except:
        print("Unknown error")
