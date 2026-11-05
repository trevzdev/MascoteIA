"""
Launcher do Mascote Flutuante Desktop (PyQt6)
Ponto de entrada para inicializar a aplicação com suporte a DPI alto,
tema moderno, sem bordas e sempre no topo.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Adiciona o diretório base ao sys.path para importações locais
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from desktop_ui.floating_window import FloatingMascotWindow


def main():
    """Inicializa e executa o Mascote Flutuante Desktop."""
    app = QApplication(sys.argv)
    app.setApplicationName("MascoteIA")
    app.setOrganizationName("MascoteIA Security")

    # Garante fechamento limpo se a janela for fechada
    app.setQuitOnLastWindowClosed(True)

    # Cria e exibe a janela flutuante
    window = FloatingMascotWindow()
    window.show()

    print("\n========================================================")
    print("  🤖 Mascote Desktop Flutuante Iniciado com Sucesso!")
    print("  📌 Características:")
    print("     - Janela Sem Bordas (Frameless)")
    print("     - Sempre no Topo (Always-on-top)")
    print("     - Fundo 100% Translúcido")
    print("     - Arraste Livre com o Botão Esquerdo do Mouse")
    print("     - Comandos por Texto e Áudio (Microfone)")
    print("     - Menu de Opções com Botão Direito")
    print("========================================================\n")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

