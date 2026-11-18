import os
import datetime
import json
from pathlib import Path
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db, engine
from app.models import (
    User, Gig, GigPackage, Order, Milestone, Deliverable,
    ProjectRequest, Proposal, Message, Review, WalletTransaction, NDAContract
)
from app.auth import hash_password
from app.services.escrow import calculate_fees
from app.services.watermark import apply_watermark, generate_non_image_preview
from app.config import settings

def seed():
    print("🌱 Inicializando base de datos y sembrando datos de prueba en Gigly...")
    init_db()
    db: Session = SessionLocal()

    try:
        if db.query(User).count() > 0:
            print("ℹ️ La base de datos ya contiene registros. Omitiendo seed repetido.")
            db.close()
            return
    except Exception:
        pass

    password_hash = hash_password("password123")

    # 1. Create Users
    u_freelancer = User(
        username="demo_freelancer",
        email="freelancer@gigly.com",
        full_name="Alex Gómez",
        password_hash=password_hash,
        bio="Arquitecto Full-Stack Senior & Especialista en Python, FastAPI, React y Arquitecturas Cloud. Más de 8 años de experiencia.",
        avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200&auto=format&fit=crop&q=80",
        current_mode="seller",
        wallet_balance=1240.0,
        escrow_balance=350.0,
        rating_avg=5.0,
        reviews_count=18
    )

    u_buyer = User(
        username="demo_client",
        email="client@gigly.com",
        full_name="Carlos Mendoza",
        password_hash=password_hash,
        bio="CEO en Startup SaaS. Buscando talento freelance de alto impacto para proyectos web y móviles.",
        avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=200&auto=format&fit=crop&q=80",
        current_mode="buyer",
        wallet_balance=850.0,
        escrow_balance=0.0
    )

    u_designer = User(
        username="sofia_ux",
        email="sofia@gigly.com",
        full_name="Sofía Castillo",
        password_hash=password_hash,
        bio="Diseñadora UI/UX y Brand Strategist. Especialista en Figma, Design Systems y Microinteracciones que convierten.",
        avatar_url="https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=200&auto=format&fit=crop&q=80",
        current_mode="seller",
        wallet_balance=620.0,
        escrow_balance=150.0,
        rating_avg=4.9,
        reviews_count=24
    )

    u_admin = User(
        username="admin_gigly",
        email="admin@gigly.com",
        full_name="SuperAdmin Gigly",
        password_hash=hash_password("admin123"),
        bio="Administrador Principal de la Plataforma Gigly.",
        avatar_url="https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&auto=format&fit=crop&q=80",
        current_mode="seller",
        wallet_balance=0.0,
        escrow_balance=0.0,
        is_admin=True,
        is_verified=True
    )

    db.add_all([u_freelancer, u_buyer, u_designer, u_admin])
    db.commit()
    db.refresh(u_freelancer)
    db.refresh(u_buyer)
    db.refresh(u_designer)

    # 2. Create Initial Wallet Transactions
    tx1 = WalletTransaction(
        user_id=u_buyer.id,
        type="deposit",
        amount=1000.0,
        description="Depósito inicial para contrataciones en Gigly"
    )
    tx2 = WalletTransaction(
        user_id=u_freelancer.id,
        type="escrow_release",
        amount=1240.0,
        description="Liberación de fondos de proyectos completados (Gigly Escrow)"
    )
    db.add_all([tx1, tx2])
    db.commit()

    # 3. Create Gigs with 3-tier packages
    g1 = Gig(
        seller_id=u_freelancer.id,
        title="Desarrollo de API REST y Microservicios de Alto Rendimiento con Python y FastAPI",
        slug="desarrollo-api-rest-fastapi-python",
        description="Diseño y desarrollo endpoints seguros, asíncronos y altamente escalables con Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL y documentación automática OpenAPI/Swagger.\n\nIncluye integración con autenticación JWT, hashing bcrypt, validaciones Pydantic y soporte para despliegue en Render, AWS o Docker.",
        category="Programación & Tech",
        sub_category="Desarrollo Backend",
        tags="Python, FastAPI, API, Backend, PostgreSQL",
        image_url="https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=800&auto=format&fit=crop&q=80",
        requires_nda=True,
        allows_retainer=True,
        retainer_monthly_price=350.0,
        rating_avg=5.0,
        rating_count=12,
        orders_count=14
    )

    g2 = Gig(
        seller_id=u_designer.id,
        title="Diseño de Interfaces Web y Móviles UI/UX Profesionales en Figma con Design System",
        slug="diseno-interfaces-ui-ux-figma-web",
        description="Creación de experiencias digitales intuitivas y visualmente impactantes. Entrego archivos Figma organizados por componentes reutilizables, tipografías, paleta de colores y prototipo interactivo testeable.",
        category="Diseño & Creatividad",
        sub_category="UI/UX",
        tags="Figma, UI, UX, Web Design, Prototipo",
        image_url="https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=800&auto=format&fit=crop&q=80",
        requires_nda=False,
        allows_retainer=True,
        retainer_monthly_price=280.0,
        rating_avg=4.9,
        rating_count=9,
        orders_count=11
    )

    g3 = Gig(
        seller_id=u_freelancer.id,
        title="Creación de Plataformas Web Modernas Full-Stack con FastAPI y Tailwind CSS",
        slug="plataforma-web-fullstack-fastapi-tailwind",
        description="Desarrollo integral de sitios web dinámicos, paneles administrativos o aplicaciones SaaS con frontend moderno en Tailwind CSS y Alpine.js con backend Python robusto.",
        category="Programación & Tech",
        sub_category="Desarrollo Web Full-Stack",
        tags="FullStack, Python, Tailwind, Web, SaaS",
        image_url="https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&auto=format&fit=crop&q=80",
        requires_nda=True,
        allows_retainer=False,
        rating_avg=5.0,
        rating_count=6,
        orders_count=7
    )

    db.add_all([g1, g2, g3])
    db.commit()
    db.refresh(g1)
    db.refresh(g2)
    db.refresh(g3)

    # Packages for Gig 1
    p1_basic = GigPackage(
        gig_id=g1.id,
        tier="basic",
        name="API Base Esencial",
        description="Hasta 4 endpoints CRUD, base de datos SQLite/PostgreSQL y documentación Swagger.",
        delivery_days=2,
        revisions=2,
        price=60.0,
        features=json.dumps(["4 Endpoints CRUD", "Documentación Swagger automática", "Entrega en 48 horas"])
    )
    p1_std = GigPackage(
        gig_id=g1.id,
        tier="standard",
        name="Microservicio Completo",
        description="Hasta 12 endpoints con autenticación JWT, roles, hash seguro y validaciones Pydantic.",
        delivery_days=4,
        revisions=4,
        price=140.0,
        features=json.dumps(["12 Endpoints seguros", "Autenticación JWT & Bcrypt", "Soporte Pagos por Hitos", "Pruebas unitarias"])
    )
    p1_prem = GigPackage(
        gig_id=g1.id,
        tier="premium",
        name="Arquitectura Enterprise",
        description="Sistema completo backend con WebSockets, colas de tareas, Dockerfile y despliegue en Render.",
        delivery_days=7,
        revisions=-1,
        price=290.0,
        features=json.dumps(["Endpoints ilimitados", "WebSockets en tiempo real", "Configuración Render & Docker", "Revisiones ilimitadas", "Soporte prioritario"])
    )

    # Packages for Gig 2
    p2_basic = GigPackage(
        gig_id=g2.id,
        tier="basic",
        name="Landing Page UI",
        description="Diseño de 1 página de aterrizaje en Figma con versión escritorio y móvil.",
        delivery_days=3,
        revisions=2,
        price=75.0,
        features=json.dumps(["1 Página completa", "Mobile & Desktop", "Componentes Figma"])
    )
    p2_std = GigPackage(
        gig_id=g2.id,
        tier="standard",
        name="Aplicación Web (5 Pantallas)",
        description="Diseño UI de hasta 5 vistas con flujo de usuario y prototipo interactivo.",
        delivery_days=5,
        revisions=3,
        price=160.0,
        features=json.dumps(["5 Vistas clave", "Prototipo interactivo", "Guía de estilos"])
    )
    p2_prem = GigPackage(
        gig_id=g2.id,
        tier="premium",
        name="Design System Completo",
        description="Sistema de diseño exhaustivo, wireframes, prototipo de alta fidelidad y entrega lista para devs.",
        delivery_days=8,
        revisions=-1,
        price=320.0,
        features=json.dumps(["Design System exhaustivo", "Vistas ilimitadas", "Exportación de activos SVG", "Revisiones ilimitadas"])
    )

    db.add_all([p1_basic, p1_std, p1_prem, p2_basic, p2_std, p2_prem])
    db.commit()

    # 4. Create Reverse Project Request
    req1 = ProjectRequest(
        buyer_id=u_buyer.id,
        title="Desarrollo de Pasarela de Pagos Escrow y Billetera Virtual para E-commerce",
        category="Programación & Tech",
        description="Buscamos un desarrollador backend experimentado en Python que nos ayude a implementar un módulo de custodia de fondos (Escrow) con cálculo automático de comisiones y panel de transacciones contables.",
        budget=450.0,
        delivery_days=10,
        requires_nda=True,
        allows_milestones=True,
        status="open",
        proposals_count=2
    )
    db.add(req1)
    db.commit()
    db.refresh(req1)

    prop1 = Proposal(
        request_id=req1.id,
        seller_id=u_freelancer.id,
        cover_letter="Hola Carlos. He desarrollado múltiples sistemas de custodia y transacciones financieras en Python con SQLAlchemy y FastAPI. Puedo estructurar los estados de retención y liberación en 3 hitos claros garantizando trazabilidad total.",
        offered_price=420.0,
        offered_days=8,
        status="pending"
    )
    prop2 = Proposal(
        request_id=req1.id,
        seller_id=u_designer.id,
        cover_letter="Puedo aportar el diseño UX/UI de la interfaz de usuario de la billetera y el flujo visual para la pasarela de pagos.",
        offered_price=250.0,
        offered_days=6,
        status="pending"
    )
    db.add_all([prop1, prop2])
    db.commit()

    # 5. Create Live Order with Escrow, Milestones and Watermarked Deliverable
    fees = calculate_fees(140.0)
    order1 = Order(
        order_number="GIG-2605-B9F2A1",
        buyer_id=u_buyer.id,
        seller_id=u_freelancer.id,
        gig_id=g1.id,
        package_id=p1_std.id,
        title="Microservicio Completo - Desarrollo de API REST y Microservicios",
        description="Desarrollo de microservicio con 12 endpoints y autenticación.",
        base_amount=fees["base_amount"],
        buyer_fee=fees["buyer_fee"],
        seller_fee=fees["seller_fee"],
        total_buyer_paid=fees["total_buyer_paid"],
        seller_net_amount=fees["seller_net_amount"],
        status="in_review",
        is_milestone_based=True,
        nda_required=True,
        nda_signed=True,
        nda_signed_at=datetime.datetime.utcnow() - datetime.timedelta(days=1),
        nda_signature_text="Alex Gómez",
        delivery_deadline=datetime.datetime.utcnow() + datetime.timedelta(days=3)
    )
    db.add(order1)
    db.commit()
    db.refresh(order1)

    # Milestones for Order 1
    m1 = Milestone(
        order_id=order1.id,
        order_index=1,
        title="Fase 1: Modelo de Datos y Autenticación",
        description="Estructura SQLAlchemy y endpoints de login/registro.",
        amount=60.0,
        due_days=2,
        status="approved",
        approved_at=datetime.datetime.utcnow() - datetime.timedelta(hours=12)
    )
    m2 = Milestone(
        order_id=order1.id,
        order_index=2,
        title="Fase 2: Lógica de Negocio y Endpoints CRUD",
        description="Implementación de los 12 endpoints y validaciones.",
        amount=80.0,
        due_days=2,
        status="delivered"
    )
    db.add_all([m1, m2])
    db.commit()

    # Sample deliverable with watermark preview
    demo_img_path = settings.UPLOAD_DELIVERIES_DIR / "sample_api_preview.png"
    watermarked_demo_path = settings.UPLOAD_WATERMARKED_DIR / "watermark_sample_api_preview.jpg"
    
    # Generate placeholder image if it doesn't exist
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (900, 500), color=(26, 29, 36))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "GIGLY DEMO WORK - ARCHIVO ENTREGABLE DEL FREELANCER", fill=(20, 184, 166))
    d.text((50, 100), "API REST de Alto Rendimiento - Microservicio Completo", fill=(234, 236, 239))
    d.text((50, 150), "Documentación OpenAPI y Esquemas Pydantic Validados", fill=(176, 181, 189))
    img.save(demo_img_path)

    apply_watermark(demo_img_path, watermarked_demo_path)

    deliverable1 = Deliverable(
        order_id=order1.id,
        milestone_id=m2.id,
        uploader_id=u_freelancer.id,
        file_title="Entrega de Fase 2 - Arquitectura de Endpoints y Documentación",
        notes="He subido la arquitectura de la Fase 2 para tu revisión. Puedes inspeccionar la vista previa protegida en la bóveda.",
        original_file_path=str(demo_img_path),
        watermarked_file_path=str(watermarked_demo_path),
        is_image=True,
        file_size=245000
    )
    db.add(deliverable1)

    # Chat messages for Order 1
    msg1 = Message(
        order_id=order1.id,
        sender_id=u_buyer.id,
        content="🚀 Pedido #GIG-2605-B9F2A1 iniciado con éxito. Fondos retenidos en Gigly Escrow.",
        is_system_message=True
    )
    msg2 = Message(
        order_id=order1.id,
        sender_id=u_freelancer.id,
        content="¡Hola Carlos! Gracias por la confianza. He firmado el NDA digital y comienzo con la Fase 1 hoy mismo."
    )
    msg3 = Message(
        order_id=order1.id,
        sender_id=u_buyer.id,
        content="Excelente Alex. Si necesitas coordinar algún detalle técnico podemos activar una videollamada por aquí."
    )
    msg4 = Message(
        order_id=order1.id,
        sender_id=u_freelancer.id,
        content="📦 He cargado los entregables de la Fase 2 en la bóveda protegida. ¡Quedo atento a tus comentarios!"
    )
    db.add_all([msg1, msg2, msg3, msg4])

    # Completed Order for review demonstration
    order2 = Order(
        order_number="GIG-2604-A7C8E2",
        buyer_id=u_buyer.id,
        seller_id=u_freelancer.id,
        gig_id=g1.id,
        package_id=p1_basic.id,
        title="API Base Esencial - Desarrollo de API REST",
        description="Entrega inicial de API CRUD.",
        base_amount=60.0,
        buyer_fee=1.8,
        seller_fee=6.0,
        total_buyer_paid=61.8,
        seller_net_amount=54.0,
        status="completed"
    )
    db.add(order2)
    db.commit()
    db.refresh(order2)

    rev = Review(
        order_id=order2.id,
        gig_id=g1.id,
        buyer_id=u_buyer.id,
        seller_id=u_freelancer.id,
        rating=5,
        comment="Excelente profesional. Código limpio, entrega anticipada y comunicación impecable. La protección de Gigly Escrow me dio muchísima tranquilidad durante todo el proceso."
    )
    db.add(rev)
    db.commit()

    db.close()
    print("✅ Siembra de datos completada con éxito. Cuentas creadas y listas para usar.")

if __name__ == "__main__":
    seed()
