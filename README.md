# BPM Calculator Release 1

## Windows

1. Pak de ZIP volledig uit.
2. Dubbelklik op `start_windows.bat`.
3. Wacht tot BPM Wijzer automatisch in je browser opent. De calculator staat op `http://127.0.0.1:8765/calculator`.

Laat het zwarte servervenster open tijdens het rekenen. Sluit dat venster of druk op Ctrl+C om de server te stoppen. Python 3 moet op Windows geïnstalleerd zijn. Als dit ontbreekt (of Windows alleen de Microsoft Store-snelkoppeling vindt), meldt het startvenster dit. Installeer Python via de genoemde downloadpagina en kies tijdens de installatie voor **Add python.exe to PATH**. De benodigde Python-module wordt daarna automatisch geïnstalleerd als die ontbreekt.

Laat **CO₂-methode** op **Automatisch bepalen** staan als je niet weet welke methode bij de opgegeven uitstoot hoort. De calculator maakt dan een aanname op basis van de eerste toelating: NEDC vóór juli 2020 en WLTP vanaf juli 2020. Let op: advertenties kunnen bij oudere auto's een WLTP-waarde tonen. Bij een datum vóór juli 2020 is de uitkomst alleen passend als de ingevoerde CO₂-waarde aansluit bij de gekozen methode. Controleer dit op het CoC of bij de RDW.

Bij de uitkomst toont de calculator de tariefopties die zijn vergeleken en welke optie de laagste bruto BPM oplevert. De forfaitaire afschrijving wordt daarna op iedere optie op dezelfde manier toegepast.

## macOS / Linux

Voer `./start_mac_linux.sh` uit en open `http://127.0.0.1:8765`.

Open `index.html` niet rechtstreeks via `file://`: de berekening gebruikt de lokale server en de BPM-engine. De startpagina staat op `/`; de calculator behoudt op `/calculator` de Release-1-interface met vijf invoervelden.

## Website / hosting

Dezelfde pagina en berekenings-API kunnen op Python-hosting draaien met Waitress:

1. Installeer de pakketten uit `requirements.txt`.
2. Start `python run_hosted.py` (de hosting kan `PORT` instellen).
3. Laat de site via HTTPS door de hosting of reverse proxy aanbieden.

`Procfile` is aanwezig voor platformen die dat formaat gebruiken. De site en API moeten onder dezelfde oorsprong beschikbaar zijn, omdat de calculator de API op `/api/release1-calculate` aanspreekt. De lokale `server.py` en `start_windows.bat` blijven bedoeld voor testen op de eigen computer. Kies vóór publieke lancering een hostingplatform en controleer daar HTTPS, foutmeldingen, invoerlimieten en de volledige berekening.

Voor Render staat `render.yaml` klaar met een gratis Python-webservice voor de test, Frankfurt-regio en `/health`-controle. De gratis service kan na inactiviteit tijdelijk slapen. Importeer dit bestand pas wanneer de projectbestanden in een Git-repository staan en de eigenaar zelf het Render-account beheert. Kies vóór een echte openbare lancering bewust een passend betaald plan. De pagina `/privacy` is een concept: contactgegevens, verantwoordelijke websitehouder en de uiteindelijke hosting-/loginstellingen moeten vóór openbare lancering worden ingevuld en gecontroleerd.
