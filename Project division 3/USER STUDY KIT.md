# USER STUDY KIT: get real evidence from 5-10 households
Purpose: your teacher wants real users and real results. Even 5 households over 5-7 days gives honest evidence. Everything here is voluntary and private.

## 1. Rules (read first)
- Ask permission before anything. Participants can stop and ask to delete their data at any time.
- Do not collect names, addresses, bill photos with personal details, or faces. Use a code like `H01`, `H02` in your notes.
- If someone uploads a bill photo, they must tick the consent box and you must tell them it is analysed by an AI service.
- Do not claim savings or accuracy you did not measure.

## 2. Consent message (send before they start)
**English:**
"Hi! I'm testing a student project, Solar Care AI, that helps households estimate their solar needs and daily electricity use. I'd like you to try it for about a week. It takes about 20 seconds a day after the first setup (10-15 minutes). I will store your appliance list and daily numbers under a code, not your name. Photos you upload are analysed by an AI service and not kept by the app. You can stop and ask me to delete your data any time. Is that okay?"

**Roman Urdu:**
"Assalam o Alaikum! Main apne student project 'Solar Care AI' ko test kar raha/rahi hoon. Yeh app gharon ko batati hai ke unhe kitna solar chahiye aur rozana bijli kaise use karni chahiye. Aap isay taqreeban ek hafta try kar sakte hain. Pehli dafa setup mein 10-15 minute lagenge, phir rozana sirf 20 second. Main aap ka naam nahi, sirf ek code (jaise H01) ke saath appliances ki list aur rozana ke numbers rakhunga/rakhungi. Jo photos aap upload karenge unhe AI service analyse karti hai, app unhe save nahi karti. Aap kabhi bhi rok sakte hain aur data delete karwa sakte hain. Kya aap ijazat dete hain?"

## 3. What each household does
**Day 0 (10-15 min):** open the link, sign up, add home (city), photograph or add main appliances, correct the list, set hours per day.
**Day 1-7 (20 sec):** open Check-in, tap "Same as usual" or change AC hours, outage hours, guests; if easy, type the meter reading (kWh) from the electricity meter.
**Day 7 (3 min):** open the Plan and Today pages, then answer the feedback form below.

## 4. Daily reminder message (copy and send each evening)
English: "Reminder: 20-second check-in today in Solar Care AI. Tap 'Same as usual' and add your meter reading if you can. Thanks!"
Roman Urdu: "Yaad dahani: aaj ka 20 second ka check-in Solar Care AI mein kar dein. 'Same as usual' dabayein aur agar ho sake to meter reading likh dein. Shukriya!"

## 5. Feedback form (6 questions; Google Form or WhatsApp)
1. Was setting up your appliance list easy? (1 = very hard, 5 = very easy)
2. How many items did you have to correct after the photo detection? (0 / 1-2 / 3-5 / more)
3. Did the solar estimate feel believable? (1-5) and why?
4. Was the daily prediction close to your meter reading? (much higher / a bit higher / close / a bit lower / much lower / didn't check)
5. Did you try any suggestion (e.g., moving the washing machine or pump to the day)? (yes / no / not possible) What happened?
6. Would you use this before buying solar? (yes / maybe / no) What confused you most?

## 6. Tracking sheet (one row per household)
Columns: code, city, setup minutes, items detected, items corrected, days checked in, meter readings entered, prediction error (see below), usefulness 1-5, trust 1-5, would use? (y/m/n), main complaint, consent given (y/n), data deleted on request (y/n).

## 7. How to compute results (honest and simple)
- **Setup effort:** average minutes; average items corrected / items detected.
- **Daily prediction error:** for days with a meter reading: |predicted kWh - meter kWh| / meter kWh, averaged per home, then across homes. Compare with the "7-day average" baseline if you have enough days.
- **Usefulness and trust:** averages with the number of responses (e.g., "4.2/5 from n=6").
- **Always state the sample size and duration** ("6 households, 5-7 days") and that results are preliminary.
- Real numbers go in `docs/evaluation.md` and slide 10; never mix synthetic results into these tables.

## 8. After the study
- Delete anyone's data who asks. Save only the anonymised tracking sheet.
- Screenshot 3 failure cases (blur anything personal) for the presentation.