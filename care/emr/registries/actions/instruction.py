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
