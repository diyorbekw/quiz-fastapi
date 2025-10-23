import requests
import random

BASE_URL = "http://localhost:1234"

# 1️⃣ Fanlar (kategoriya) ro‘yxati
categories = [
    {"name": "Matematika", "description": "Hisob-kitob, tenglamalar, mantiqiy masalalar.", "emoji": "🧮", "time": 15},
    {"name": "Ingliz tili", "description": "Lug‘at, grammatika, tarjima va gap tuzish mashqlari.", "emoji": "🇬🇧", "time": 12},
    {"name": "Biologiya", "description": "Organizmlar, inson tanasi, tabiat va hayot jarayonlari.", "emoji": "🧬", "time": 14},
    {"name": "Fizika", "description": "Kuch, harakat, energiya, elektr va mexanika asoslari.", "emoji": "⚛️", "time": 15}
]

category_ids = {}

# 2️⃣ Kategoriyalarni yaratish
for i, cat in enumerate(categories, start=1):
    res = requests.post(f"{BASE_URL}/categories", json=cat)
    if res.status_code in (200, 201):
        print(f"[✅] {cat['name']} yaratildi (id={i})")
    else:
        print(f"[⚠️] {cat['name']} yaratishda xato: {res.text}")
    category_ids[cat["name"]] = i

# 3️⃣ Savollarni to‘g‘ri formatda yaratish uchun yordamchi funksiya
def make_question(question, options, correct_answer, category_id):
    """Variantlar bilan birga to‘g‘ri formatdagi savol obyektini qaytaradi."""
    letters = ["A", "B", "C", "D"]
    correct_index = options.index(correct_answer)
    return {
        "question": question,
        "a_var": options[0],
        "b_var": options[1],
        "c_var": options[2],
        "d_var": options[3],
        "answer": letters[correct_index],  # faqat A/B/C/D yuboriladi
        "category_id": category_id
    }

# 4️⃣ Savol generatorlari

def create_math_questions():
    questions = []
    # 15 ta arifmetik misol
    for _ in range(15):
        a, b = random.randint(3, 20), random.randint(3, 20)
        op = random.choice(["+", "-", "*"])
        if op == "+":
            ans = a + b
        elif op == "-":
            ans = a - b
        else:
            ans = a * b
        question = f"{a} {op} {b} = ?"
        options = [str(ans), str(ans + 2), str(ans - 1), str(ans + 3)]
        random.shuffle(options)
        questions.append(make_question(question, options, str(ans), category_ids["Matematika"]))

    # 10 ta so‘zli/tenglamali masalalar
    word_problems = [
        ("Bir do‘konda 15 dona olma bor edi. 7 tasi sotildi. Nechta olma qoldi?", ["6", "8", "7", "9"], "8"),
        ("Bir poyezd soatiga 80 km tezlikda 3 soat yurdi. Masofa qancha?", ["240 km", "160 km", "200 km", "320 km"], "240 km"),
        ("Tenglama: 2x + 6 = 14. x =", ["4", "3", "6", "5"], "4"),
        ("Kvadrat tomoni 5 sm. Yuzi nechiga teng?", ["25", "20", "10", "15"], "25"),
        ("Tenglama: 3x - 9 = 0. x =", ["3", "6", "9", "12"], "3"),
        ("Mashina 60 km/soat tezlikda 2,5 soat yurdi. Masofa =", ["150 km", "100 km", "120 km", "180 km"], "150 km"),
        ("(8 + 2) × 3 =", ["30", "20", "24", "18"], "30"),
        ("9 × 9 =", ["81", "72", "99", "90"], "81"),
        ("Tenglama: x/4 = 5. x =", ["10", "15", "20", "25"], "20"),
        ("Tort 8 bo‘lakka bo‘lindi. 3 bo‘lagi yeyildi. Nechta qoldi?", ["3", "4", "5", "6"], "5"),
    ]
    for q in word_problems:
        opts = q[1][:]
        random.shuffle(opts)
        questions.append(make_question(q[0], opts, q[2], category_ids["Matematika"]))
    return questions


def create_english_questions():
    qdata = [
        ("Translate: 'Book' means ___ in Uzbek.", ["Kitob", "Daftar", "Qalam", "Ruchka"], "Kitob"),
        ("Choose the correct form: She ___ very well.", ["sings", "sing", "sang", "singing"], "sings"),
        ("Opposite of 'hot' is ___", ["cold", "warm", "cool", "heat"], "cold"),
        ("Which is a pronoun?", ["He", "Run", "Quickly", "Big"], "He"),
        ("Translate: 'I am a student.'", ["Men o‘quvchiman", "Men o‘qituvchiman", "Men ishlayman", "Men talaba emasman"], "Men o‘quvchiman"),
        ("Choose the correct article: ___ cat is black.", ["The", "A", "An", "No article"], "The"),
        ("Find the synonym of 'small'.", ["tiny", "large", "big", "huge"], "tiny"),
        ("Choose the right preposition: She lives ___ London.", ["in", "at", "on", "under"], "in"),
        ("Plural of 'child' is ___", ["children", "childs", "childes", "childer"], "children"),
        ("Translate: 'My name is John.'", ["Mening ismim Jon", "Uning ismi Jon", "Isming Jon", "Bu Jon"], "Mening ismim Jon"),
        ("What color is the sky?", ["blue", "green", "black", "yellow"], "blue"),
        ("Find the verb: He can run fast.", ["run", "fast", "He", "can"], "run"),
        ("Choose correct sentence.", ["She go to school", "She goes to school", "She going to school", "She go school"], "She goes to school"),
        ("Translate: 'Teacher' means ___", ["O‘qituvchi", "Talaba", "Doktor", "Haydovchi"], "O‘qituvchi"),
        ("Fill in the blank: They ___ playing football.", ["are", "is", "am", "was"], "are"),
        ("Past tense of 'go' is ___", ["went", "goed", "gone", "goes"], "went"),
        ("Translate: 'Car' means ___", ["Mashina", "Velosiped", "Samolyot", "Qayiq"], "Mashina"),
        ("Opposite of 'good' is ___", ["bad", "ugly", "evil", "sad"], "bad"),
        ("What is the plural of 'man'?", ["men", "mans", "mens", "man"], "men"),
        ("Choose: She ___ coffee every morning.", ["drinks", "drink", "drinking", "drunk"], "drinks"),
        ("Translate: 'School' means ___", ["Maktab", "Bozor", "Uy", "Do‘kon"], "Maktab"),
        ("Find the adjective: The apple is red.", ["red", "apple", "is", "the"], "red"),
        ("Choose: He ___ a doctor.", ["is", "are", "am", "be"], "is"),
        ("Translate: 'Sun' means ___", ["Quyosh", "Oy", "Yulduz", "Bulut"], "Quyosh"),
        ("Find the question: ___ are you?", ["How", "What", "When", "Where"], "How"),
    ]
    questions = []
    for q in qdata:
        opts = q[1][:]
        random.shuffle(opts)
        questions.append(make_question(q[0], opts, q[2], category_ids["Ingliz tili"]))
    return questions


def create_biology_questions():
    qdata = [
        ("Inson yuragi nechta kameradan iborat?", ["2", "3", "4", "5"], "4"),
        ("Fotosintez qayerda sodir bo‘ladi?", ["Xloroplast", "Mitochondriya", "Ribosoma", "Yadro"], "Xloroplast"),
        ("DNK to‘liq nomi nima?", ["Dezoksiribonuklein kislota", "Ribonuklein kislota", "Oqsil", "Yog‘"], "Dezoksiribonuklein kislota"),
        ("Inson tanasida nechta suyak bor?", ["206", "200", "210", "180"], "206"),
        ("Qonning qaysi qismi kislorod tashiydi?", ["Eritrotsit", "Leikotsit", "Trombosit", "Plazma"], "Eritrotsit"),
        ("O‘simlik ildizining vazifasi?", ["Suv so‘rish", "Fotosintez", "Nafas olish", "Changlanish"], "Suv so‘rish"),
        ("Insonning eng katta organi?", ["Teri", "Yurak", "Jigar", "O‘pka"], "Teri"),
        ("Ko‘payish jarayoni qayerda sodir bo‘ladi?", ["Jinsiy organlarda", "O‘pka", "Yurak", "Miya"], "Jinsiy organlarda"),
        ("Qaysi hayvon sutemizuvchidir?", ["Fil", "Qush", "Baliq", "Tovuq"], "Fil"),
        ("Nafas olish organi?", ["O‘pka", "Jigar", "Teri", "Yurak"], "O‘pka"),
        ("DNKda qanday baza mavjud emas?", ["Uratsil", "Adenin", "Timin", "Sitozin"], "Uratsil"),
        ("Qaysi qon guruhi universal donor?", ["O(I)", "A(II)", "B(III)", "AB(IV)"], "O(I)"),
        ("Qon bosimi nima bilan o‘lchanadi?", ["Tonomet", "Termometr", "Barometr", "Voltmeter"], "Tonomet"),
        ("Ko‘zning qorachig‘i nimani boshqaradi?", ["Yorug‘lik kirishini", "Ko‘rish nervini", "Ko‘z suyuqligini", "Rangni"], "Yorug‘lik kirishini"),
        ("Inson tanasining eng kichik suyaklari qayerda?", ["Quloqda", "Qo‘lda", "Oyog‘da", "Burunda"], "Quloqda"),
        ("Jigar vazifasi nima?", ["Zararli moddalardan tozalaydi", "Nafas oladi", "Harakat qiladi", "Ko‘radi"], "Zararli moddalardan tozalaydi"),
        ("Inson tanasida nechta miya bo‘limi bor?", ["3", "2", "4", "5"], "3"),
        ("Qon aylanish tizimining markazi?", ["Yurak", "Jigar", "Miya", "O‘pka"], "Yurak"),
        ("Fotosintez uchun nima kerak?", ["Quyosh nuri", "Qon", "Azot", "Tuz"], "Quyosh nuri"),
        ("Insonda nechta xromosoma mavjud?", ["46", "48", "44", "42"], "46"),
        ("Nerv tizimining asosiy hujayrasi?", ["Neyron", "Eritrotsit", "Suyak", "Mushak"], "Neyron"),
        ("Qonning rangini nima beradi?", ["Gemoglobin", "Suv", "Kislorod", "Yog‘"], "Gemoglobin"),
        ("Insonda nafas olish tezligi nechta/min?", ["16-18", "10", "25", "5"], "16-18"),
        ("Qaysi organ hazm tizimiga tegishli?", ["Oshqozon", "Yurak", "Miya", "O‘pka"], "Oshqozon"),
        ("Qon plazmasi nimalardan iborat?", ["Suv va oqsillar", "Yog‘ va gazlar", "Tuz va kislorod", "Kislota va suv"], "Suv va oqsillar"),
    ]
    questions = []
    for q in qdata:
        opts = q[1][:]
        random.shuffle(opts)
        questions.append(make_question(q[0], opts, q[2], category_ids["Biologiya"]))
    return questions


def create_physics_questions():
    qdata = [
        ("Kuchning birligi nima?", ["Nyuton", "Joul", "Pascal", "Vatt"], "Nyuton"),
        ("Energiyaning o‘lchov birligi?", ["Joul", "Vatt", "Volt", "Amper"], "Joul"),
        ("F = m * a formulasi nimani ifodalaydi?", ["Nyutonning 2-qonuni", "Ohm qonuni", "Boyl qonuni", "Arximed qonuni"], "Nyutonning 2-qonuni"),
        ("Suv 100°C da nima qiladi?", ["Qaynaydi", "Muzlaydi", "Bug‘lanmaydi", "Qotadi"], "Qaynaydi"),
        ("Zaryad birligi?", ["Kulon", "Volt", "Amper", "Ohm"], "Kulon"),
        ("Ohm qonuni formulasi?", ["U = I * R", "P = I * V", "F = m * a", "Q = m * c"], "U = I * R"),
        ("Gravitatsiya kuchini kim kashf qilgan?", ["Nyuton", "Galiley", "Faradey", "Einshteyn"], "Nyuton"),
        ("Suvning zichligi qancha?", ["1000 kg/m³", "1 kg/m³", "500 kg/m³", "100 kg/m³"], "1000 kg/m³"),
        ("Tezlikning formulasi?", ["v = s/t", "a = F/m", "p = m*v", "E = m*c²"], "v = s/t"),
        ("Ish birligi?", ["Joul", "Vatt", "Kulon", "Amper"], "Joul"),
        ("Tok kuchi birligi?", ["Amper", "Volt", "Om", "Joul"], "Amper"),
        ("Quvvat formulasi?", ["P = U * I", "F = m * a", "V = s/t", "E = m*c²"], "P = U * I"),
        ("Ohmning belgisi?", ["Ω", "Δ", "μ", "π"], "Ω"),
        ("Harorat o‘lchov birligi?", ["Kelvin", "Pascal", "Joul", "Volt"], "Kelvin"),
        ("Potensial energiya formulasi?", ["E = mgh", "E = ½mv²", "F = ma", "P = IV"], "E = mgh"),
        ("Suv bosimi qaysi birlikda o‘lchanadi?", ["Pascal", "Volt", "Joul", "Watt"], "Pascal"),
        ("Tezlanish formulasi?", ["a = (v - v₀)/t", "v = s/t", "P = IV", "U = IR"], "a = (v - v₀)/t"),
        ("Nyutonning 1-qonuni nima haqida?", ["Inersiya", "Tezlanish", "Kuch", "Harorat"], "Inersiya"),
        ("Issiqlik o‘lchov birligi?", ["Joul", "Kelvin", "Pascal", "Vatt"], "Joul"),
        ("Arximed kuchi nimaga teng?", ["Og‘irlikka teng", "Zichlikka teng", "Haroratga teng", "Zaryadga teng"], "Og‘irlikka teng"),
        ("Zaryad belgisi?", ["Q", "I", "V", "R"], "Q"),
        ("Tok kuchi belgisi?", ["I", "U", "R", "Q"], "I"),
        ("Harakatning asosiy kattaliklari?", ["Masofa, vaqt, tezlik", "Energiyalar", "Zichlik va harorat", "Kuch va mass"], "Masofa, vaqt, tezlik"),
        ("Energiyaning saqlanish qonuni kimga tegishli?", ["Lomonosov", "Galiley", "Ohm", "Faradey"], "Lomonosov"),
        ("E = m * c² formulasi kimniki?", ["Einshteyn", "Nyuton", "Tesla", "Arximed"], "Einshteyn"),
    ]
    questions = []
    for q in qdata:
        opts = q[1][:]
        random.shuffle(opts)
        questions.append(make_question(q[0], opts, q[2], category_ids["Fizika"]))
    return questions


# 5️⃣ Barcha savollarni birlashtirish
all_questions = (
    create_math_questions()
    + create_english_questions()
    + create_biology_questions()
    + create_physics_questions()
)

# 6️⃣ APIga yuborish
for i, q in enumerate(all_questions, start=1):
    res = requests.post(f"{BASE_URL}/questions", json=q)
    if res.status_code in (200, 201):
        print(f"[✅] {i}-savol qo‘shildi")
    else:
        print(f"[⚠️] Xato {i}-savolda: {res.text}")
