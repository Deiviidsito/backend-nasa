#!/usr/bin/env python3
"""
Script de prueba simple para Fase 2 - Depuración
"""

import sys
import os
import traceback
sys.path.insert(0, os.path.dirname(__file__))

def main():
    print("🧪 PRUEBA SIMPLE - FASE 2")
    print("=" * 50)
    
    try:
        # Importar módulos
        print("1️⃣ Importando módulos...")
        from process_fusion import process_fusion
        print("   ✅ Módulos importados")
        
        # Ejecutar procesamiento
        print("2️⃣ Ejecutando procesamiento...")
        dataset = process_fusion()
        print("   ✅ Procesamiento completado")
        
        # Mostrar resultado
        print("3️⃣ Resultado:")
        print(f"   • Dimensiones: {dict(dataset.dims)}")
        print(f"   • Variables: {list(dataset.data_vars.keys())}")
        
        # Verificar risk_score
        if "risk_score" in dataset.data_vars:
            risk = dataset.risk_score
            print(f"   • Risk Score: [{float(risk.min()):.1f}, {float(risk.max()):.1f}]")
        
        print("🎉 ¡ÉXITO!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)