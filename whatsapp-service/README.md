# Voice Pipeline : 

```User sends a Whatsapp voice note --> Gets a voice note back with reccommendations and essential content```


## Flow for one Incoming Message : 
```
-> Twilio Posts to /webhook then a voice note arrives 

-> We download the ausio Twilio give us the url to

-> Send that url to Sarvam Saaras (STT) api

-> hand the transcrIpt to reccommendation engine

-> Get the text back and send to Sarvam Bulbul (TTS)

-> Get the audio from Sarvam Bulbul 

-> Save it locally and send to Twilio

```