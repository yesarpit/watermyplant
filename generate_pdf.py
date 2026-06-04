from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER

def generate_pdf(filename):
    doc = SimpleDocTemplate(filename, pagesize=letter,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=HexColor("#2D4A22"),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        name='HeadingStyle',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=HexColor("#4A7A38"),
        spaceBefore=20,
        spaceAfter=10
    )
    
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        textColor=HexColor("#1A2615"),
        spaceAfter=10
    )
    
    promo_style = ParagraphStyle(
        name='PromoStyle',
        parent=styles['Normal'],
        fontSize=12,
        leading=18,
        textColor=HexColor("#E27D60"),
        spaceBefore=20,
        spaceAfter=10,
        alignment=TA_CENTER
    )

    story = []

    # Title
    story.append(Paragraph("The 2026-27 Guide to Indian Plant Care", title_style))
    story.append(Paragraph("Surviving Extreme Summers and Monsoons", ParagraphStyle(name='Sub', parent=title_style, fontSize=14, spaceAfter=40)))

    # Introduction
    story.append(Paragraph("Caring for indoor and balcony plants in India requires adapting to extreme seasons. From scorching 45°C summers to heavy, humid monsoons, your plants go through intense stress. Here are our unique tips for the upcoming years.", normal_style))
    
    # Tip 1
    story.append(Paragraph("1. The 'Monsoon Fast'", heading_style))
    story.append(Paragraph("During the Indian monsoon, ambient humidity skyrockets. Many plant parents continue their summer watering schedule, which leads to immediate root rot. The trick is to implement a 'Monsoon Fast'. For indoor plants like Monsteras and ZZ plants, cut watering by 70%. Let the soil dry out completely to the bottom of the pot. The plants will absorb enough moisture from the air to survive.", normal_style))

    # Tip 2
    story.append(Paragraph("2. The DIY Neem Oil Emulsion", heading_style))
    story.append(Paragraph("Mealybugs love the Indian heat and humidity. Instead of harsh chemicals, make a true emulsion. Mix 1 teaspoon of pure cold-pressed Neem Oil with 1/2 teaspoon of mild liquid dish soap FIRST. Mix them until they form a milky paste, THEN add 1 liter of warm water. Spraying this in the early morning prevents leaf burn and suffocates pests organically.", normal_style))

    # Tip 3
    story.append(Paragraph("3. Terracotta vs. Plastic in the Indian Heat", heading_style))
    story.append(Paragraph("Terracotta pots are a lifesaver in the summer because they breathe, preventing roots from boiling in wet soil. However, during the monsoon, terracotta absorbs ambient moisture and can grow algae, keeping the soil constantly wet. If you use terracotta, ensure it is kept in a well-ventilated area with a fan during the rainy season to prevent mold.", normal_style))

    story.append(Spacer(1, 40))

    # Conclusion / Promotion
    story.append(Paragraph("<b>The Ultimate Solution: watermyplant.in</b>", promo_style))
    story.append(Paragraph("Going away on a business trip or vacation? Don't let your plants suffer through the heat wave or the monsoon without care. <br/><br/>At <b>watermyplant.in</b>, we provide professional, vetted gardeners who understand the local climate perfectly. We offer Pan-India services starting at just ₹20/day.", promo_style))
    story.append(Paragraph("<b>Book via WhatsApp: 8087404471</b>", ParagraphStyle(name='WhatsApp', parent=promo_style, fontSize=14, textColor=HexColor("#2D4A22"))))

    # Build PDF
    doc.build(story)

if __name__ == "__main__":
    generate_pdf("2026-27-indian-plant-care-guide.pdf")
