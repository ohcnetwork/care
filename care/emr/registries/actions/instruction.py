class ActionInstructionRegistry:
    _instructions = {}

    @classmethod
    def register(cls, instruction) -> None:
        if instruction.slug in cls._instructions:
            err = f"Instruction with slug {instruction.slug} already registered"
            raise ValueError(err)
        cls._instructions[instruction.slug] = instruction

    @classmethod
    def get_instruction(cls, slug: str):
        return cls._instructions.get(slug)

    @classmethod
    def render_all_instructions(cls) -> list[dict]:
        return [cls._instructions[x].render_dict() for x in cls._instructions]
