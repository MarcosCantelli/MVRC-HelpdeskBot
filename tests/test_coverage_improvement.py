import pytest
from types import SimpleNamespace
from app.api.app import (
    create_ticket_service,
    app as flask_app,
)
from app.bot.bot import run_bot


# ================================
# API COVERAGE TESTS
# ================================
class TestAPITicketCreationSuccess:
    """Testes para cobrir sucesso na criação de tickets"""
    
    def test_create_ticket_complete_with_ai_suggestion(self):
        """Testa criação completa com sugestão de IA"""
        data = {
            "user": "usuario@example.com",
            "description": "Computador não liga",
            "category": "hardware",
            "subcategory": "desktop",
            "ai_suggestion": "Verificar fonte de alimentação"
        }
        
        result, status = create_ticket_service(data)
        
        assert status == 201
        assert "id" in result
        assert result["status"] == "aberto"
        assert result["ticket_code"].startswith("TK")

    def test_create_ticket_software_category(self):
        """Testa criação com categoria software"""
        data = {
            "user": "test@test.com",
            "description": "Windows não abre",
            "category": "software"
        }
        
        result, status = create_ticket_service(data)
        
        assert status == 201
        assert result["ticket_code"].startswith("TK")


class TestAPITicketCreationErrors:
    """Testes para cobrir erros na criação de tickets"""
    
    def test_create_ticket_missing_user(self):
        """Testa erro quando falta usuário"""
        data = {
            "description": "Problema"
        }
        
        result, status = create_ticket_service(data)
        
        assert status == 400
        assert "error" in result
        assert "obrigatórios" in result["error"]

    def test_create_ticket_missing_description(self):
        """Testa erro quando falta descrição"""
        data = {
            "user": "test@test.com"
        }
        
        result, status = create_ticket_service(data)
        
        assert status == 400
        assert "error" in result

    def test_create_ticket_none_data(self):
        """Testa erro quando data é None"""
        result, status = create_ticket_service(None)
        
        assert status == 400


class TestAPIListTickets:
    """Testes para cobertura de listagem de tickets"""
    
    def test_list_tickets_success(self):
        """Testa listagem de tickets com sucesso"""
        # Primeiro criar um ticket
        create_ticket_service({
            "user": "test@test.com",
            "description": "Teste",
            "category": "hardware"
        })
        
        # Testar a rota
        client = flask_app.test_client()
        response = client.get("/tickets")
        
        assert response.status_code == 200
        data = response.get_json()
        assert isinstance(data, list)


class TestBotHandlersCompleteness:
    """Testes para cobrir todos os handlers e fluxos do bot"""
    
    @pytest.mark.asyncio
    async def test_start_command_handler(self):
        """Testa comando /start do bot"""
        app = run_bot(token="fake-token")
        
        # Encontra o handler de start
        start_handlers = [
            h for h in app.handlers[0]
            if h.__class__.__name__ == "CommandHandler"
            and hasattr(h, 'commands')
            and 'start' in h.commands
        ]
        
        assert len(start_handlers) > 0

    @pytest.mark.asyncio
    async def test_tickets_command_handler(self):
        """Testa comando /tickets do bot"""
        app = run_bot(token="fake-token")
        
        # Verifica que o handler de tickets foi adicionado
        handlers_str = str(app.handlers[0])
        assert "CommandHandler" in handlers_str

    @pytest.mark.asyncio
    async def test_handle_message_invalid_choice(self):
        """Testa mensagem com escolha inválida"""
        app = run_bot(token="fake-token")
        
        message_handlers = [
            h for h in app.handlers[0] 
            if h.__class__.__name__ == "MessageHandler"
        ]
        handler = message_handlers[0]
        
        class FakeMessage:
            def __init__(self):
                self.texts = []
                self.text = "Opção inválida"
            
            async def reply_text(self, text, reply_markup=None):
                self.texts.append(text)
        
        class FakeUser:
            def __init__(self):
                self.id = 123
                self.full_name = "Teste"
                self.username = "teste"
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = FakeUser()
        
        update = FakeUpdate()
        context = SimpleNamespace(user_data={})
        
        await handler.callback(update, context)
        
        # Deve responder com ajuda de fluxo, sem depender de hardware/software
        assert any("descreva" in t.lower() or "problema" in t.lower() or "chamado" in t.lower() 
                   for t in update.message.texts)

    @pytest.mark.asyncio
    async def test_handle_message_equipment_step(self):
        """Testa fluxo de seleção de equipamento"""
        app = run_bot(token="fake-token")
        
        message_handlers = [
            h for h in app.handlers[0] 
            if h.__class__.__name__ == "MessageHandler"
        ]
        handler = message_handlers[0]
        
        class FakeMessage:
            def __init__(self):
                self.texts = []
                self.text = ""
            
            async def reply_text(self, text, reply_markup=None):
                self.texts.append(text)
        
        class FakeUser:
            def __init__(self):
                self.id = 123
                self.full_name = "Teste"
                self.username = "teste"
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = FakeUser()
        
        update = FakeUpdate()
        context = SimpleNamespace(user_data={"step": "descricao"})
        update.message.text = "Notebook com tela preta"

        await handler.callback(update, context)

        assert context.user_data["descricao"] == "Notebook com tela preta"
        assert context.user_data["step"] == "aguardando_confirmacao"
    @pytest.mark.asyncio
    async def test_handle_message_description_simple_problem(self, monkeypatch):
        """Testa fluxo com problema simples (não cria ticket)"""
        app = run_bot(token="fake-token")
        
        message_handlers = [
            h for h in app.handlers[0] 
            if h.__class__.__name__ == "MessageHandler"
        ]
        handler = message_handlers[0]
        
        class FakeMessage:
            def __init__(self):
                self.texts = []
                self.text = ""
            
            async def reply_text(self, text, reply_markup=None):
                self.texts.append(text)
        
        class FakeUser:
            def __init__(self):
                self.id = 123
                self.full_name = "Teste"
                self.username = "teste"
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = FakeUser()
        
        update = FakeUpdate()
        context = SimpleNamespace(user_data={"step": "descricao"})
        update.message.text = "internet lenta"
        
        async def mock_criar_ticket(update, user, context):
            pass
        
        monkeypatch.setattr("app.bot.bot.criar_ticket", mock_criar_ticket)
        
        await handler.callback(update, context)
        
        # Para problema simples, deve pedir confirmação
        assert context.user_data["step"] == "aguardando_confirmacao"

    @pytest.mark.asyncio
    async def test_handle_message_confirmation_yes(self):
        """Testa resposta 'sim' à confirmação"""
        app = run_bot(token="fake-token")
        
        message_handlers = [
            h for h in app.handlers[0] 
            if h.__class__.__name__ == "MessageHandler"
        ]
        handler = message_handlers[0]
        
        class FakeMessage:
            def __init__(self):
                self.texts = []
                self.text = ""
            
            async def reply_text(self, text, reply_markup=None):
                self.texts.append(text)
        
        class FakeUser:
            def __init__(self):
                self.id = 123
                self.full_name = "Teste"
                self.username = "teste"
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = FakeUser()
        
        update = FakeUpdate()
        context = SimpleNamespace(user_data={"step": "aguardando_confirmacao"})
        update.message.text = "sim"
        
        await handler.callback(update, context)
        
        assert any("✅" in t for t in update.message.texts)
        assert context.user_data["step"] == "finalizado"

    @pytest.mark.asyncio
    async def test_handle_message_confirmation_no(self, monkeypatch):
        """Testa resposta 'não' à confirmação (cria ticket)"""
        app = run_bot(token="fake-token")
        
        message_handlers = [
            h for h in app.handlers[0] 
            if h.__class__.__name__ == "MessageHandler"
        ]
        handler = message_handlers[0]
        
        class FakeMessage:
            def __init__(self):
                self.texts = []
                self.text = ""
            
            async def reply_text(self, text, reply_markup=None):
                self.texts.append(text)
        
        class FakeUser:
            def __init__(self):
                self.id = 123
                self.full_name = "Teste"
                self.username = "teste"
        
        class FakeUpdate:
            def __init__(self):
                self.message = FakeMessage()
                self.effective_user = FakeUser()
        
        update = FakeUpdate()
        context = SimpleNamespace(user_data={"step": "aguardando_confirmacao"})
        update.message.text = "não"
        
        ticket_created = False
        
        async def mock_criar_ticket(update, user, context):
            nonlocal ticket_created
            ticket_created = True
        
        monkeypatch.setattr("app.bot.bot.criar_ticket", mock_criar_ticket)
        
        await handler.callback(update, context)
        
        assert context.user_data["step"] == "finalizado"
