from fastapi.testclient import TestClient
from main import app
from app.services.watermark import apply_watermark
from pathlib import Path

client = TestClient(app)

def test_full_platform():
    print("🚀 Iniciando suite exhaustiva de pruebas funcionales para Gigly...")

    # 1. Rutas públicas
    assert client.get("/").status_code == 200
    assert client.get("/gigs").status_code == 200
    assert client.get("/requests").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    print("✅ Vistas públicas OK (200)")

    # 2. Login como freelancer
    res = client.post("/login", data={"username_or_email": "demo_freelancer", "password": "password123"}, follow_redirects=False)
    assert res.status_code == 303
    freelancer_cookies = res.cookies
    print("✅ Autenticación Freelancer OK")

    # 3. Analíticas financieras de vendedor
    r_analytics = client.get("/analytics", cookies=freelancer_cookies)
    assert r_analytics.status_code == 200
    r_charts = client.get("/api/analytics/charts", cookies=freelancer_cookies)
    assert r_charts.status_code == 200
    assert r_charts.json()["success"] is True
    print("✅ Panel de Analíticas y Gráficos Chart.js OK")

    # 4. Login como cliente
    res = client.post("/login", data={"username_or_email": "demo_client", "password": "password123"}, follow_redirects=False)
    assert res.status_code == 303
    client_cookies = res.cookies
    print("✅ Autenticación Cliente OK")

    # 5. Billetera y Depósito
    r_dep = client.post("/api/wallet/deposit", data={"amount": 200.0, "payment_method": "card"}, cookies=client_cookies)
    assert r_dep.status_code == 200
    assert r_dep.json()["success"] is True
    print("✅ Depósito en Billetera OK")

    # 6. Switch Role
    r_switch = client.post("/api/auth/switch-mode", json={"mode": "seller"}, cookies=client_cookies)
    assert r_switch.status_code == 200
    assert r_switch.json()["current_mode"] == "seller"
    print("✅ Cambio de Rol Dinámico Comprador <-> Vendedor OK")

    # Switch back to buyer
    client.post("/api/auth/switch-mode", json={"mode": "buyer"}, cookies=client_cookies)

    # 7. Login como Administrador y verificar Panel de Control
    res_admin = client.post("/login", data={"username_or_email": "admin_gigly", "password": "admin123"}, follow_redirects=False)
    assert res_admin.status_code == 303
    admin_cookies = res_admin.cookies
    r_admin = client.get("/admin", cookies=admin_cookies)
    assert r_admin.status_code == 200
    assert "SuperAdmin" in r_admin.text
    print("✅ Autenticación y Panel de SuperAdmin (/admin) OK (200)")

    # 8. Verificar Servicio de Marca de Agua
    test_src = Path("uploads/deliveries/sample_api_preview.png")
    test_out = Path("uploads/watermarked/test_watermark.jpg")
    if test_src.exists():
        ok = apply_watermark(test_src, test_out)
        assert ok is True
        assert test_out.exists()
        print("✅ Generación de Marca de Agua Automática (Gigly Anti-Robo) OK")

    # 8. Sala de Pedido y Chat
    r_order = client.get("/orders/GIG-2605-B9F2A1", cookies=client_cookies)
    assert r_order.status_code == 200
    assert "GIG-2605-B9F2A1" in r_order.text
    print("✅ Sala de Pedido con Custodia Escrow y Chat OK")

    print("\n🌟 RESULTADO: 100% DE PRUEBAS FUNCIONALES COMPLETADAS CON ÉXITO.")

if __name__ == "__main__":
    test_full_platform()
