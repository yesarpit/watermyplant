from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

def generate_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=HexColor("#2D4A22"),
        spaceAfter=20,
        alignment=TA_CENTER
    )
    
    chapter_style = ParagraphStyle(
        name='ChapterStyle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=HexColor("#2D4A22"),
        spaceBefore=20,
        spaceAfter=20
    )
    
    heading_style = ParagraphStyle(
        name='HeadingStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor("#4A7A38"),
        spaceBefore=15,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=18,
        textColor=HexColor("#1A2615"),
        spaceAfter=15,
        alignment=TA_JUSTIFY
    )
    
    promo_style = ParagraphStyle(
        name='PromoStyle',
        parent=styles['Normal'],
        fontSize=14,
        leading=20,
        textColor=HexColor("#E27D60"),
        spaceBefore=30,
        spaceAfter=20,
        alignment=TA_CENTER
    )

    story = []

    # PAGE 1: TITLE & INDEX
    story.append(Spacer(1, 100))
    story.append(Paragraph("The 2026-27 Comprehensive Guide", title_style))
    story.append(Paragraph("to Indian Plant Care", title_style))
    story.append(Spacer(1, 50))
    try:
        story.append(Image('images/hero.png', width=400, height=300))
    except:
        pass
    
    story.append(PageBreak())

    # PAGE 2: INDEX
    story.append(Paragraph("Index", chapter_style))
    chapters = [
        "Chapter 1: Understanding Indian Climate Zones",
        "Chapter 2: The Monsoon Fast - Watering Techniques",
        "Chapter 3: Best Indoor Plants for Indian Summers",
        "Chapter 4: Thriving Balcony Gardens in Full Sun",
        "Chapter 5: DIY Pest Control & The Neem Oil Emulsion",
        "Chapter 6: Terracotta vs. Plastic - The Great Debate",
        "Chapter 7: Crafting the Perfect Indian Potting Mix",
        "Chapter 8: Managing Extreme Coastal Humidity",
        "Chapter 9: Surviving the Northern Indian Winter",
        "Chapter 10: The Ultimate Plant Care Solution"
    ]
    for idx, chap in enumerate(chapters):
        story.append(Paragraph(f"{chap} .................... Page {idx + 3}", normal_style))
    
    story.append(PageBreak())

    # PAGE 3: Chapter 1
    story.append(Paragraph("Chapter 1: Understanding Indian Climate Zones", chapter_style))
    story.append(Paragraph("India's geography offers a diverse range of climates, from the arid deserts of Rajasthan to the humid coastal regions of Kerala and the freezing winters of the Himalayas. Understanding your micro-climate is the first step to successful plant parenting.", normal_style))
    story.append(Paragraph("In the North (Delhi, Punjab), plants face extreme scorching summers up to 45°C and freezing winters down to 2°C. Tropical plants often go dormant here. In the South (Chennai, Bangalore, Kerala), the temperature is moderate to hot year-round, but humidity plays a massive role.", normal_style))
    story.append(Paragraph("Before buying a plant, always assess your home's natural light, ambient temperature, and whether you run an air conditioner all day, which dries out the air significantly. A plant that thrives in a Mumbai balcony might instantly die in a dry Delhi apartment without a humidifier.", normal_style))
    story.append(Spacer(1, 400)) # Force text to stretch down
    story.append(PageBreak())

    # PAGE 4: Chapter 2
    story.append(Paragraph("Chapter 2: The Monsoon Fast", chapter_style))
    story.append(Paragraph("During the Indian monsoon, ambient humidity skyrockets. Many plant parents continue their summer watering schedule, which leads to immediate root rot. The trick is to implement a 'Monsoon Fast'.", normal_style))
    try:
        story.append(Image('images/pdf_monsoon.png', width=300, height=225))
    except:
        pass
    story.append(Paragraph("For indoor plants like Monsteras and ZZ plants, cut watering by 70%. Let the soil dry out completely to the bottom of the pot. The plants will absorb enough moisture from the air to survive. Check the drainage holes of your pots daily to ensure no water is logging at the bottom.", normal_style))
    story.append(Paragraph("It is also crucial to move plants away from direct rain exposure if they are prone to fungal infections. Succulents, in particular, should be brought entirely indoors or kept under a shed during July and August.", normal_style))
    story.append(Spacer(1, 350))
    story.append(PageBreak())

    # PAGE 5: Chapter 3
    story.append(Paragraph("Chapter 3: Best Indoor Plants for Indian Summers", chapter_style))
    story.append(Paragraph("Not all indoor plants can survive the harsh Indian summer, especially when the AC is turned off during the day while you are at work. You need resilient, drought-tolerant species.", normal_style))
    story.append(Paragraph("1. Sansevieria (Snake Plant): The ultimate survivor. It thrives on neglect, purifies the air, and handles extreme heat beautifully.", normal_style))
    story.append(Paragraph("2. Zamioculcas Zamiifolia (ZZ Plant): Stores water in its rhizomes, meaning it can go weeks without a drop of water.", normal_style))
    story.append(Paragraph("3. Epipremnum aureum (Money Plant): A staple in Indian households. It grows rapidly and can easily be propagated in water.", normal_style))
    story.append(Spacer(1, 350))
    story.append(PageBreak())

    # PAGE 6: Chapter 4
    story.append(Paragraph("Chapter 4: Thriving Balcony Gardens in Full Sun", chapter_style))
    story.append(Paragraph("If you have a South or West-facing balcony in India, your plants will be baked by the afternoon sun. Choosing the right outdoor plants is critical.", normal_style))
    try:
        story.append(Image('images/pdf_terracotta.png', width=300, height=225))
    except:
        pass
    story.append(Paragraph("Bougainvillea, Hibiscus, and Plumeria (Champa) are fantastic choices. They love direct sunlight and require minimal watering once established. To protect their roots from boiling, consider double-potting or adding a thick layer of organic mulch (like dried leaves or coco peat) on top of the soil.", normal_style))
    story.append(Spacer(1, 200))
    story.append(PageBreak())

    # PAGE 7: Chapter 5
    story.append(Paragraph("Chapter 5: DIY Pest Control", chapter_style))
    story.append(Paragraph("Mealybugs and spider mites love the Indian heat and humidity. Instead of harsh chemical pesticides, you can make a true organic emulsion at home.", normal_style))
    try:
        story.append(Image('images/pdf_neem.png', width=300, height=225))
    except:
        pass
    story.append(Paragraph("The Neem Oil Recipe: Mix 1 teaspoon of pure cold-pressed Neem Oil with 1/2 teaspoon of mild liquid dish soap FIRST. Mix them until they form a milky paste, THEN add 1 liter of warm water. Spraying this in the early morning prevents leaf burn and suffocates pests organically. Repeat every 7 days until the infestation clears.", normal_style))
    story.append(Spacer(1, 350))
    story.append(PageBreak())

    # PAGE 8: Chapter 6
    story.append(Paragraph("Chapter 6: Terracotta vs. Plastic", chapter_style))
    story.append(Paragraph("Terracotta pots are a lifesaver in the summer because they breathe, preventing roots from boiling in wet soil. The porous clay allows excess water to evaporate quickly, which is perfect for over-waterers.", normal_style))
    story.append(Paragraph("However, during the monsoon, terracotta absorbs ambient moisture and can grow algae, keeping the soil constantly wet. If you use terracotta, ensure it is kept in a well-ventilated area with a fan during the rainy season. Plastic pots retain moisture longer, making them better for ferns and calatheas, but they require much stricter drainage control.", normal_style))
    story.append(Spacer(1, 350))
    story.append(PageBreak())

    # PAGE 9: Chapter 7 & 8
    story.append(Paragraph("Chapter 7: The Perfect Indian Potting Mix", chapter_style))
    story.append(Paragraph("Never use plain red soil (laal mitti) directly from a nursery for indoor plants. It compacts into a brick when dry and turns to mud when wet.", normal_style))
    try:
        story.append(Image('images/pdf_soil.png', width=300, height=225))
    except:
        pass
    story.append(Paragraph("A good standard mix for Indian indoor plants is: 40% Coco Peat (for moisture retention), 30% Perlite or Pumice (for aeration), 20% Vermicompost (for nutrients), and 10% Garden Soil. This ensures water drains out within 10 seconds of watering.", normal_style))
    
    story.append(Paragraph("Chapter 8: Managing Extreme Coastal Humidity", chapter_style))
    story.append(Paragraph("In cities like Mumbai or Chennai, 90% humidity is common. While tropical plants love this, it also breeds fungal infections. Ensure good airflow by keeping windows open or fans running. Avoid misting your plants—they already have enough moisture in the air!", normal_style))
    story.append(Spacer(1, 150))
    story.append(PageBreak())

    # PAGE 10: Chapter 9 & 10
    story.append(Paragraph("Chapter 9: Surviving the Northern Winter", chapter_style))
    story.append(Paragraph("In North India, winters can drop near freezing. Tropical plants will stop growing entirely. Stop fertilizing from November to February. Reduce watering drastically, as the soil will take much longer to dry out. Keep plants away from cold window panes.", normal_style))
    
    story.append(Paragraph("Chapter 10: The Ultimate Plant Care Solution", chapter_style))
    story.append(Paragraph("Even with all this knowledge, the hardest part of plant parenting is leaving them behind when you travel.", normal_style))
    
    story.append(Paragraph("<b>watermyplant.in</b>", promo_style))
    story.append(Paragraph("Going away on a business trip, family vacation, or just visiting your hometown? Don't let your plants suffer through the heat wave or the monsoon without care. At <b>watermyplant.in</b>, we provide professional, vetted gardeners who understand the local climate perfectly. We offer Pan-India services starting at just ₹20/day.", ParagraphStyle(name='P', parent=normal_style, alignment=TA_CENTER)))
    story.append(Paragraph("<b>Book via WhatsApp: 8087404471</b>", ParagraphStyle(name='WhatsApp', parent=promo_style, fontSize=16, textColor=HexColor("#2D4A22"))))

    # Build PDF
    doc.build(story)

if __name__ == "__main__":
    generate_pdf("2026-27-indian-plant-care-guide.pdf")
