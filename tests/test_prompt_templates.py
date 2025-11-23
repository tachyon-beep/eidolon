from eidolon.planning.prompt_templates import PromptTemplateLibrary, AgentRole


def test_system_decomposer_prompt_design():
    prompt = PromptTemplateLibrary.get_system_decomposer_prompt(
        user_request="Add JWT auth",
        project_path="/repo",
        subsystems=["api", "models"],
        role=AgentRole.DESIGN,
    )
    assert "system" in prompt and "user" in prompt
    assert "Add JWT auth" in prompt["user"]
    assert "api, models" in prompt["user"]


def test_subsystem_decomposer_prompt():
    prompt = PromptTemplateLibrary.get_subsystem_decomposer_prompt(
        subsystem_task="Add login flow",
        target_subsystem="auth",
        existing_modules=["auth_service.py"],
    )
    assert "Subsystem Task" in prompt["user"]
    assert "auth_service.py" in prompt["user"]


def test_module_decomposer_prompt():
    prompt = PromptTemplateLibrary.get_module_decomposer_prompt(
        module_task="Implement AuthService",
        target_module="auth_service.py",
        existing_classes=[],
        existing_functions=[],
    )
    assert "Implement AuthService" in prompt["user"]
    assert "auth_service.py" in prompt["user"]


def test_function_planner_prompt():
    prompt = PromptTemplateLibrary.get_function_generator_prompt(
        function_name="login",
        instruction="write login function",
        module_context="context",
    )
    assert "login" in prompt["user"]
    assert "context" in prompt["user"]
