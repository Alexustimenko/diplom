"""Public information architecture inspired by the current clerk.by route tree.

Product data continues to come from Rolmark's database. The article route list
is loaded from the separately authorized local editorial archive.
"""

from dataclasses import dataclass

from app.article_data import article_slugs


@dataclass(frozen=True)
class Category:
    slug: str
    name: str
    description: str
    terms: tuple[str, ...] = ()
    brand: str | None = None
    group: str = "chairs"


# Historical route-research snapshot kept only for audit traceability. Runtime
# navigation, filters, routes and admin forms never read this tuple; SQL Server
# is the sole catalog taxonomy source of truth.
LEGACY_ROUTE_REFERENCE = (
    Category("nedorogo-kupit-kreslo", "Недорогие кресла", "Практичные модели с доступной ценой для дома и офиса.", group="featured"),
    Category("kresla_everprof", "Кресла Everprof", "Модели бренда Everprof из нашего каталога.", brand="everprof"),
    Category("kresla_metta", "Кресла МЕТТА", "Модели бренда МЕТТА из нашего каталога.", brand="метта"),
    Category("kresla_akshome", "Кресла AksHome", "Модели бренда AksHome из нашего каталога.", brand="akshome"),
    Category("kresla_chairman", "Кресла CHAIRMAN", "Модели бренда CHAIRMAN из нашего каталога.", brand="chairman"),
    Category("kresla_byurokrat", "Кресла Бюрократ", "Модели бренда Бюрократ из нашего каталога.", brand="бюрократ"),
    Category("kresla_brabix", "Кресла BRABIX", "Модели бренда BRABIX из нашего каталога.", brand="brabix"),
    Category("kresla_hitech", "Кресла Hi-Tech", "Современные кресла для технологичных интерьеров.", terms=("hi-tech", "hitech", "хай-тек")),
    Category("kresla_klassa_premium", "Кресла класса премиум", "Представительные модели с расширенным комфортом.", terms=("премиум", "premium", "кожа")),
    Category("gejmerskie_kresla", "Геймерские кресла", "Кресла для длительных игровых сессий и работы.", terms=("геймер", "игров", "gaming")),
    Category("kompyuternye_kresla", "Компьютерные кресла", "Универсальные модели для рабочего места за компьютером.", terms=("компьютер", "оператор")),
    Category("kreslo-dlya-personala", "Кресла для персонала", "Рабочие кресла для сотрудников и операторов.", terms=("персонал", "оператор", "офисное кресло")),
    Category("novye_modeli_ofisnyh_kresel", "Новые модели офисных кресел", "Последние добавленные модели нашего ассортимента.", group="featured"),
    Category("kreslo-rukovoditelya", "Кресла руководителя", "Представительные кресла для кабинета руководителя.", terms=("руководител", "директор")),
    Category("kresla_dlya_posetitelej", "Кресла для посетителей", "Стулья и кресла для переговорных и зон ожидания.", terms=("посетител", "переговор", "стул")),
    Category("kojanoe-kreslo", "Кожаные кресла", "Модели с обивкой из кожи и экокожи.", terms=("кожа", "экокожа", "кожзам")),
    Category("kresla_dlya_otdyha", "Кресла для отдыха", "Комфортные кресла для домашних и общественных зон отдыха.", terms=("отдых", "релакс")),
    Category("kreslo-reklajner", "Кресла-реклайнеры", "Кресла с механизмом изменения положения спинки.", terms=("реклайнер", "recliner")),
    Category("kresla_ergoline", "Кресла ERGOLINE", "Эргономичные модели линейки ERGOLINE.", brand="ergoline"),
    Category("plastikovye_sidenya", "Пластиковые сиденья", "Износостойкие пластиковые сиденья и стулья.", terms=("пластик", "пластиков"), group="furniture"),
    Category("detskie_stulya", "Детские стулья", "Мебель для комфортного и безопасного рабочего места ребёнка.", terms=("детск", "kids"), group="furniture"),
    Category("rastuschaya_mebel_dlya_detej", "Растущая мебель для детей", "Регулируемая мебель, которая адаптируется к росту ребёнка.", terms=("детск", "kids", "растущ"), group="furniture"),
    Category("skladnaya_mebel", "Складная мебель", "Компактная мебель для дома, офиса и мероприятий.", terms=("складн",), group="furniture"),
    Category("kuhonnye_stulya_kupit_nedorogo", "Кухонные стулья", "Стулья для кухни и обеденной зоны.", terms=("кухон", "обеденн"), group="furniture"),
    Category("barnye_stulya", "Барные стулья", "Высокие стулья для барных стоек и кухонных островов.", terms=("барн",), group="furniture"),
    Category("ofisnie-divany", "Офисные диваны", "Диваны для приёмных, переговорных и зон ожидания.", terms=("диван",), group="furniture"),
    Category("steklyannye_stoly", "Стеклянные столы", "Столы со стеклянными элементами для современных интерьеров.", terms=("стекл", "стол"), group="furniture"),
    Category("ofisnaya_mebel", "Офисная мебель", "Мебель для организации функционального рабочего пространства.", terms=("офис", "стол", "шкаф", "тумб"), group="furniture"),
    Category("komplektuyushchiye-dlia-ofisnykh-kresel-i-stulyev", "Комплектующие", "Запасные части и комплектующие для кресел и стульев.", terms=("запчаст", "комплект", "крестовин", "ролик", "механизм"), group="parts"),
    Category("krestoviny", "Крестовины", "Основания и крестовины для ремонта офисных кресел.", terms=("крестовин",), group="parts"),
    Category("roliki", "Ролики", "Колёсные опоры и ролики для кресел.", terms=("ролик", "колес"), group="parts"),
    Category("mehanizmy", "Механизмы", "Механизмы регулировки и качания офисных кресел.", terms=("механизм", "топ-ган", "мультиблок", "пиастр"), group="parts"),
    Category("tovary_dlya_sporta_nedorogo", "Товары для спорта", "Практичные товары для домашней и офисной активности.", terms=("спорт", "тренаж"), group="legacy"),
    Category("tovary_dlia_otdyha_i_turizma", "Товары для отдыха и туризма", "Товары для выездного отдыха и организации временных зон.", terms=("туризм", "отдых"), group="legacy"),
)

STATIC_PAGES = {
    "dostavka": ("Доставка", "Условия доставки", "Доставляем заказы по согласованному адресу. Срок и стоимость зависят от состава заказа и региона; менеджер подтвердит их до оформления."),
    "oplata": ("Оплата", "Способы оплаты", "Доступные способы оплаты и комплект документов согласуются при подтверждении заказа. Для организаций предусмотрено безналичное оформление."),
    "contact": ("Контакты", "Контакты и обращения", "Свяжитесь с нами по телефону или электронной почте, чтобы уточнить наличие, совместимость и условия заказа."),
    "about": ("О нас", "О компании", "Мы подбираем офисную мебель и комплектующие, консультируем по характеристикам и помогаем с послепродажными вопросами."),
    "gift": ("Оформление заказа", "Как оформить заказ", "Выберите товар, добавьте его в корзину и укажите данные для связи. Менеджер проверит наличие и подтвердит детали."),
    "garantiya_zamena_vozvrat": ("Гарантия", "Гарантия, замена и возврат", "Гарантийные условия зависят от товара и производителя. Сохраните документы о покупке и свяжитесь с нами перед передачей товара."),
    "kreslo-v-rassrochky": ("Рассрочка", "Рассрочка", "Покупка офисных кресел и стульев в рассрочку."),
    "sale": ("Акции", "Акции и специальные предложения", "В разделе собраны товары и условия, на которые действуют специальные предложения нашего магазина."),
    "politika_konfidentsialnosti": ("Конфиденциальность", "Политика конфиденциальности", "Мы используем предоставленные данные только для обработки обращений и заказов, а также для выполнения требований законодательства."),
    "halva": ("Оплата картой рассрочки", "Оплата картой рассрочки", "Условия оплаты картами рассрочки зависят от действующих договоров и конкретного товара. Актуальные детали сообщит менеджер."),
}


ARTICLE_SLUGS = article_slugs()

NEWS_SLUGS = (
    "chem_kresla_dlya_personala_otlichayutsya_ot_kresel_dlya_rukovoditelya",
    "chem_otlichaetsya_rassrochka_pokupki_kresla_ot_kredita",
    "kak_uhazhivat_za_ofisnymi_kreslami",
    "kak_vybrat_komfortnoe_kreslo_dlya_raboty",
    "kak_vybrat_ofisnoe_kreslo_dlya_rukovoditelya",
    "my_pereezzhaem_v_novyj_salon",
    "na_chto_obraschat_vnimanie_pri_pokupke_ofisnogo_kresla",
    "otlichnye_predlozheniya_pokupatelyam_pod_novyj_god",
    "rassmotrim_nekotorye_modeli_kresel_chairman",
    "s_nastupayuschim_novym_2019m_godom_i_rozhdestvom",
    "skidka_10_k_23_fevralya",
    "skidki_na_vse_kresla_10",
    "skladnaya_mebel_dlya_ofisa_i_doma",
    "vesennyaya_aktsiya_k_8_marta",
    "vozmozhen_raschet_po_kreditnym_i_debetovym_kartochkam_po_vsej_rb",
    "vseh_nashih_dorogih_klientov_s_novym_2018_godom_",
    "vybiraem_barnye_stulya",
    "vybiraem_pravilnoe_kompyuternoe_kreslo_dlya_podrostka",
    "vybor_barnyh_stulev_dlya_kuhnistudii",
    "vybor_gejmerskogo_kresla_dxracer",
)

# Routes advertised by clerk.by/sitemap.php under its older /blog/ namespace.
LEGACY_BLOG_SLUGS = (
    "5_interesnyh_faktov_ob_ofisnyh_kreslah", "5_vazhnyh_sovetov_po_vyboru_kachestvennogo_ofisnogo_kresla",
    "byudzhetnaya_mebel", "chem_kresla_dlya_personala_otlichayutsya_ot_kresel_dlya_rukovoditelya",
    "chem_otlichaetsya_rassrochka_pokupki_kresla_ot_kredita", "chto_nuzhno_horoshemu_kreslu",
    "chto_vy_znaete_pro_ofisnuyu_mebel", "dostatochno_byudzhetnyh_ofisnyh_kresel",
    "ergonomichnye_ofisnye_kresla_chto_eto_i_kak_ih_vybrat", "gejmerskoe_kreslo_tonkosti_vybora",
    "harakteristiki-kresel", "hitrosti_vybora_gejmerskogo_kresla",
    "kak_pravilno_uhazhivat_za_ofisnoj_mebelyu", "kak_pravilno_vybrat_kompyuternoe_kreslo_dlya_doma",
    "kak_uhazhivat_za_ofisnym_divanom", "kak_uhazhivat_za_ofisnymi_kreslami",
    "kak_ustroena_ispytatelnaya_laboratoriya_kresel_chairman", "kak_vybrat_barnye_stulya_dlya_kuhni",
    "kak_vybrat_divan_v_ofis", "kak_vybrat_horoshij_kompyuternyj_stul",
    "kak_vybrat_komfortnoe_kreslo_dlya_raboty", "kak_vybrat_naibolee_udobnye_kresla",
    "kak_vybrat_ofisnoe_kreslo_dlya_rukovoditelya", "kak_vybrat_podhodyaschee_gejmerskoe_kreslo",
    "kakoe_ofisnoe_kreslo_budet_sluzhit_dolshe", "kazalos_by_chto_mozhet_byt_prosche_chem_vybor_ofisnogo_kresla_",
    "komfort_vliyaet_na_produktivnost_sotrudnikov", "kozhanoe_kreslo__vsegda_prekrasnyj_vybor",
    "kozhanye_kresla_dlya_ofisa__klassika_so_vkusom", "kozhanye_kresla_i_ih_preimuschestva",
    "kresla_iz_setchatoj_tkani", "kresla_s_setkoj_stanovyatsya_populyarnymi",
    "mebel_dlya_kabineta_rukovoditelya", "moda_na_kreslareklajner", "my_pereezzhaem_v_novyj_salon",
    "na_chto_obraschat_vnimanie_pri_pokupke_ofisnogo_kresla",
    "naibolee_rasprostranennye_nepriyatnosti_s_ofisnymi_kreslami_i_kak_ih_izbezhat",
    "naturalnaya_kozha_protiv_ekokozhi", "nemnogo_pro_ofisnuyu_mebel",
    "neobhodimo_obstavit_kabinet_rukovoditelya", "novye_divany_dlya_komfortnogo_otdyha",
    "ochen_horosho_smotryatsya_na_kresle_rukovoditelya_ruchki_iz_dereva",
    "ofisnaya_i_skladnaya_mebel_iz_kakogo_materiala_ee_vybrat",
    "ofisnoe_kreslo_dolzhno_otvechat_tselomu_kompleksu_parametrov", "ofisnoe_kreslo_xxi_veka",
    "ofisnye_kresla_dlya_personala_legko_kupit_priyatno_rabotat", "ofisnye_kresla_dolzhny_byt_solidnymi",
    "ortopedicheskie_kresla__vashe_zdorove_i_komfort", "otlichie_multibloka_ot_dmsl",
    "otlichnye_predlozheniya_pokupatelyam_pod_novyj_god", "pokupka_kompyuternyh_kresel_bu_vse_za_i_protiv",
    "pokupka_kresel_dlya_ofis", "pravilnyj_vybor_kompyuternogo_kresla", "pro_nashi_ofisnye_kresla",
    "professionalno_podhodim_k_vyboru_kompyuternogo_kresla",
    "rassmotrim_nekotorye_modeli_kresel_chairman", "remont_kompyuternogo_kresla",
    "s_nastupayuschim_novym_2019m_godom_i_rozhdestvom", "sidyachaya_rabota_stanet_komfortnee",
    "skidka_10_k_23_fevralya", "skidki_na_vse_kresla_10", "skladnaya_mebel_dlya_ofisa_i_doma",
    "skladnaya_mebel_na_vse_sluchai_zhizni", "sovremennyj_ofis",
    "sravnenie_gejmerskih_kresel_lotus_s5_signal_q054_everprof_forsage", "stroenie_ofisnogo_kresla",
    "suschestvuet_tri_osnovnyh_tipa_kresel", "tolko_luchshie_kresla", "vesennyaya_aktsiya_k_8_marta",
    "vozmozhen_raschet_po_kreditnym_i_debetovym_kartochkam_po_vsej_rb",
    "vseh_nashih_dorogih_klientov_s_novym_2018_godom_", "vybiraem_barnye_stulya",
    "vybiraem_pravilnoe_kompyuternoe_kreslo_dlya_podrostka", "vybor_barnyh_stulev_dlya_kuhnistudii",
    "vybor_gejmerskogo_kresla_dxracer", "vybor_mehanizma_dlya_kresla", "vybrat_stul_kreslo_dlja_ofisa",
    "zharkie_tseny_na_kresla_ot_rolmarktrejd",
)


def humanize_slug(slug: str) -> str:
    """Turn a legacy transliterated slug into readable neutral text."""
    words = slug.replace("-", " ").replace("_", " ").strip()
    return words[:1].upper() + words[1:]
