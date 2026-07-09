import pytest

from usdx_dl.inference import fasttext_np


def test_download_model():
    model_path = fasttext_np.download_model()
    assert model_path.exists()


def test_load_model():
    model_path = fasttext_np.download_model()
    model = fasttext_np.load_model(model_path)
    assert isinstance(model, fasttext_np.FastText)


@pytest.mark.parametrize(
    "expected_lang, sentence",
    [
        # cSpell: disable
        #
        # North/South America + Europe + Oceania
        #
        ("en", "This is a test sentence."),  # English
        ("es", "Esta es una oración de prueba."),  # Spanish
        ("fr", "Ceci est une phrase de test."),  # French
        ("de", "Dies ist ein Testsatz."),  # German
        ("it", "Questa è una frase di prova."),  # Italian
        ("pt", "Esta é uma frase de teste."),  # Portuguese
        ("nl", "Dit is een testzin."),  # Dutch
        ("sv", "Detta är en testsats."),  # Swedish
        ("no", "Dette er en testsetning."),  # Norwegian
        ("da", "Dette er en testsætning."),  # Danish
        ("fi", "Tämä on testilause."),  # Finnish
        ("pl", "To jest zdanie testowe."),  # Polish
        ("cs", "Toto je testovací věta."),  # Czech
        # ("sk", "Toto je testovacia veta."),  # Slovak
        ("hu", "Ez egy teszt mondat."),  # Hungarian
        ("ro", "Aceasta este o propoziție de testare."),  # Romanian
        ("bg", "Това е тестово изречение."),  # Bulgarian
        ("ru", "Это тестовое предложение."),  # Russian
        ("uk", "Це тестове речення."),  # Ukrainian
        ("el", "Αυτή είναι μια δοκιμαστική πρόταση."),  # Greek
        ("tr", "Bu bir test cümlesidir."),  # Turkish
        #
        # Asia
        #
        ("zh", "这是一个测试句子。"),  # Chinese
        ("ja", "これはテスト文です。"),  # Japanese
        ("ko", "이것은 테스트 문장입니다."),  # Korean
        ("ar", "هذه جملة اختبار."),  # Arabic
        ("he", "זוהי משפט בדיקה."),  # Hebrew
        ("hi", "यह एक परीक्षण वाक्य है।"),  # Hindi
        ("bn", "এটি একটি পরীক্ষামূলক বাক্য।"),  # Bengali
        ("pa", "ਇਹ ਇੱਕ ਟੈਸਟ ਵਾਕ ਹੈ।"),  # Punjabi
        ("ta", "இது ஒரு சோதனை வாக்கியம்."),  # Tamil
        ("te", "ఇది ఒక పరీక్ష వాక్యం."),  # Telugu
        ("ml", "ഇത് ഒരു ടെസ്റ്റ് വാചകം ആണ്."),  # Malayalam
        ("kn", "ಇದು ಒಂದು ಪರೀಕ್ಷಾ ವಾಕ್ಯವಾಗಿದೆ."),  # Kannada
        ("mr", "हे एक चाचणी वाक्य आहे."),  # Marathi
        ("gu", "આ એક પરીક્ષણ વાક્ય છે."),  # Gujarati
        ("or", "ଏହା ଏକ ପରୀକ୍ଷା ବାକ୍ୟ।"),  # Odia
        # ("as", "এইটো এটা পৰীক্ষা বাক্য।"),  # Assamese
        # ("ne", "यो एक परीक्षण वाक्य हो।"),  # Nepali
        ("si", "මෙය පරීක්ෂණ වාක්‍යයකි."),  # Sinhala
        ("my", "ဤသည် စမ်းသပ်မှုစာကြောင်းတစ်ခုဖြစ်သည်။"),  # Burmese
        ("km", "នេះគឺជាប្រយោគសាកល្បងមួយ។"),  # Khmer
        # ("lo", "ນີ�ນແມ່ນປະໂຫຍກກທົດສອບໜຶ່ງ."),  # Lao
        ("th", "นี่คือประโยคทดสอบหนึ่ง."),  # Thai
        ("vi", "Đây là một câu thử nghiệm."),  # Vietnamese
        ("id", "Ini adalah kalimat uji."),  # Indonesian
        # ("ms", "Ini adalah ayat ujian."),  # Malay
        #
        # Africa
        #
        # ("sw", "Hii ni sentensi ya majaribio."),  # Swahili
        # ("zu", "Lena yisivivinyo somusho."),  # Zulu
        # ("xh", "Le yisivivinyo somusho."),  # Xhosa
        ("af", "Dit is 'n toets sin."),  # Afrikaans
        ("am", "ይህ የሙከራ አንደበት ነው።"),  # Amharic
        # ("om", "Kun kunuufni qormaata dha."),  # Oromo
        # ("so", "Tani waa jumlad tijaabo ah."),  # Somali
        # ("ha", "Wannan jimla ce ta gwaji."),  # Hausa
        # ("ig", "Nke a bụ ahịrịokwu ule."),  # Igbo
        # ("yo", "Eyi jẹ gbolohun idanwo kan."),  # Yoruba
        # ("st", "Sena ke polelo ea teko."),  # Sesotho
        # ("tn", "Se ke polelo ya teko."),  # Setswana
        # ("ts", "Lena i xifaniso xa ku ringana."),  # Tsonga
        # ("ve", "Hezwi ndi mutsiko wa vhuṱungu."),  # Venda
        # ("nr", "Lena yisivivinyo somusho."),  # Southern Ndebele
        # ("ss", "Lena yisivivinyo somusho."),  # Swati
        # cSpell: enable
    ],
)
def test_langid(expected_lang: str, sentence: str):
    model = fasttext_np.load_model(quantized=True)
    pred = model.predict(sentence)
    assert pred is not None
    assert pred[0].label == expected_lang
    assert pred[0].score > 0.4
