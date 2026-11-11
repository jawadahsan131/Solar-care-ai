Claude

















08 chunk8 yolo dataset training · MD
CHUNK 8 — Own detection model: dataset and YOLO training
(Paste MASTER BRIEF first, then this card. Start TODAY because photo collection takes the longest; training happens tomorrow. Claude cannot take photos for you: the data collection in Part A is human work.)

Goal
A fine-tuned YOLO model that detects about 18 home appliance classes, trained on photos taken in Pakistani homes and shops, plus an honest evaluation. It plugs into detect_yolo.py later; until then the vision-LLM backend runs the website.

Classes (use exactly these names; they map to the type slugs)
ac_indoor, ac_outdoor, ceiling_fan, pedestal_fan, exhaust_fan, air_cooler, refrigerator, deep_freezer, microwave, electric_oven, water_dispenser, washing_machine, iron, geyser, water_pump, tv, computer (desktop or laptop), ups Mapping: ac_indoor and ac_outdoor -> type ac; computer -> desktop_pc or laptop (ask the user); others map by name. Not detected by the model (use counters in the app): LED bulbs, tube lights, chargers, routers.

Part A — Human work: collect the photos (start now)
Targets: at least 100 photos per class (150 is better) = about 2,000 photos, with multiple appliances per photo allowed. Today aim for 300 or more as a first batch.

Where: your own home, relatives', neighbors' (ask permission), shops/showrooms, markets. Some web photos are acceptable to fill gaps, but check licenses (Open Images and similar open datasets) and keep a note of the source.
Variety is more important than quantity: different brands, colors and ages; angles (front, side, from below for ceilings fans); distances (close and far); day and night lighting; cluttered rooms; partly hidden objects; two or three appliances in the same photo; dirty/dusty units.
Take 20 extra close-ups of rating plates and stickers (AC outdoor unit plate, fridge sticker, fan sticker). They are for the label-reading (OCR) test set, not for YOLO training.
Phone settings: normal photo mode (no heavy filters/HDR beauty modes), keep original orientation.
Privacy: no faces, family photos, documents or addresses in the frame. Blur anything personal before labeling.
Record for each photo: which home or shop it came from (a number such as home03). This is needed for the split.
File naming: home03_livingroom_001.jpg. Keep originals and a resized copy (longest side 1280 px).
Part B — Labeling
Tool choice (ask Claude to compare quickly): Label Studio or CVAT run locally keep your photos private; Roboflow's free plan is convenient but free projects may be public (check current terms) so do not use it for private home photos.
Labeling rules (give these to Claude to turn into a one-page guide):
Draw a tight box around each complete visible appliance.
Label partly hidden objects if at least about 40 percent is visible; skip tiny or blurry ones.
One box per unit (three fans = three boxes).
When unsure between classes, skip the object and note it.
Same box rules for every labeler (if friends help label, review 10 percent of their work).
Export in YOLO format (txt files with normalized boxes + a data.yaml).
Part C — Split correctly (common mistake)
Split by HOME/SHOP, not randomly by photo: about 70 percent of homes in train, 20 percent in validation, 10 percent in test. Photos from the same home in different splits leak information and give fake high accuracy.
Keep the test set untouched until the final evaluation.
Part D — Training notebook (ask Claude to write it as a Google Colab notebook, cell by cell)
Mount Google Drive, install ultralytics, check the GPU (Runtime -> T4).
Unzip the dataset, show class counts per split (bar chart) and 12 random labeled images as a visual check.
Train baseline: YOLO11n (or the current small Ultralytics model) pretrained weights, imgsz=640, epochs=60, batch=16, patience=15, standard augmentations. Save runs to Drive.
Evaluate on validation then test: mAP@0.5, mAP@0.5:0.95, precision, recall per class, confusion matrix.
Error analysis cell: list the 20 worst images (missed or wrong class) and look at them.
Improve in this order: (a) fix labels and add photos for weak classes, (b) more epochs / larger model (s), (c) tune image size 800, (d) class balance. Do not change the test set.
Export best.pt and ONNX; write model_card.md (classes, data counts, metrics, limits, date).
Speed test: inference time per image on CPU (the API runs on a CPU server). Target under 1 second at 640 px.
Part E — Plug into the API (later, small)
detect_yolo.py: load best.pt once; run on the resized image; confidence threshold 0.35 default (per-class overrides allowed); merge ac_indoor/ac_outdoor into type ac; return the same DetectedItem structure with source_tag="guess" for type-only detections; then reuse the existing post-processing (catalog matching) and send crops of ac_outdoor/stickers to the vision-LLM for label reading. Switch with DETECT_BACKEND=yolo. Keep vlm as a fallback when YOLO confidence is low.

What to measure and report (for the course)
Per-class AP and overall mAP@0.5 on the test split; confusion matrix; number of images and boxes per class.
Comparison table: YOLO alone vs vision-LLM alone vs YOLO + LLM for labels, on the same 100 test photos: type accuracy, percent of items the user had to edit, seconds per photo.
Honest limits: classes not covered, lighting issues, brands the model has not seen.
Acceptance for TODAY
 Class list fixed, shot list printed or saved on your phone, folder structure created.
 At least 300 photos taken or collected, each with a home id.
 Labeling tool chosen and 20 photos labeled as a test of the process.
Acceptance for tomorrow
 1,000+ photos labeled, baseline trained, first metrics table.
Handoff
HANDOFF NOTE: counts per class, tool used, where the data is stored, baseline metrics (when available).


