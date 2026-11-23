import re
import sys
from pathlib import Path


COMP = {
    "0": "0101010",
    "1": "0111111",
    "-1": "0111010",
    "D": "0001100",
    "A": "0110000",
    "!D": "0001101",
    "!A": "0110001",
    "-D": "0001111",
    "-A": "0110011",
    "D+1": "0011111",
    "A+1": "0110111",
    "D-1": "0001110",
    "A-1": "0110010",
    "D+A": "0000010",
    "D-A": "0010011",
    "A-D": "0000111",
    "D&A": "0000000",
    "D|A": "0010101",
    "M": "1110000",
    "!M": "1110001",
    "-M": "1110011",
    "M+1": "1110111",
    "M-1": "1110010",
    "D+M": "1000010",
    "D-M": "1010011",
    "M-D": "1000111",
    "D&M": "1000000",
    "D|M": "1010101",
}

DEST = {
    "": "000",
    "M": "001",
    "D": "010",
    "MD": "011",
    "A": "100",
    "AM": "101",
    "AD": "110",
    "AMD": "111",
}

JUMP = {
    "": "000",
    "JGT": "001",
    "JEQ": "010",
    "JGE": "011",
    "JLT": "100",
    "JNE": "101",
    "JLE": "110",
    "JMP": "111",
}

SYMBOL_PATTERN = re.compile(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$")


def predefined_symbols():
    symbols = {
        "SP": 0,
        "LCL": 1,
        "ARG": 2,
        "THIS": 3,
        "THAT": 4,
        "SCREEN": 16384,
        "KBD": 24576,
    }
    for number in range(16):
        symbols["R" + str(number)] = number
    return symbols


def clean_source(path):
    instructions = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, original_line in enumerate(source, start=1):
            line = original_line.split("//", 1)[0]
            line = "".join(line.split())
            if line:
                instructions.append((line, line_number))
    return instructions


def first_pass(instructions, symbols):
    rom_address = 0
    labels = {}
    for instruction, line_number in instructions:
        if instruction.startswith("("):
            if not instruction.endswith(")") or instruction.count("(") != 1:
                raise ValueError("line {}: invalid label syntax: {}".format(
                    line_number, instruction
                ))
            label = instruction[1:-1]
            if not SYMBOL_PATTERN.fullmatch(label):
                raise ValueError("line {}: invalid label name: {}".format(
                    line_number, label
                ))
            if label in symbols or label in labels:
                raise ValueError("line {}: duplicate label or reserved symbol: {}".format(
                    line_number, label
                ))
            labels[label] = rom_address
        else:
            rom_address += 1
    symbols.update(labels)
    return labels


def assemble_a_instruction(instruction, line_number, symbols, variables):
    value = instruction[1:]
    if not value:
        raise ValueError("line {}: missing value in A-instruction".format(line_number))

    if value.isdigit():
        address = int(value)
    elif SYMBOL_PATTERN.fullmatch(value):
        if value not in symbols:
            symbols[value] = variables[0]
            variables[0] += 1
        address = symbols[value]
    else:
        raise ValueError("line {}: invalid A-instruction: {}".format(
            line_number, instruction
        ))

    if address < 0 or address > 32767:
        raise ValueError("line {}: A-instruction value must be from 0 to 32767".format(
            line_number
        ))
    return format(address, "016b")


def assemble_c_instruction(instruction, line_number):
    if instruction.count("=") > 1 or instruction.count(";") > 1:
        raise ValueError("line {}: invalid C-instruction: {}".format(
            line_number, instruction
        ))

    if ";" in instruction:
        before_jump, jump = instruction.split(";", 1)
    else:
        before_jump, jump = instruction, ""

    if "=" in before_jump:
        dest, comp = before_jump.split("=", 1)
    else:
        dest, comp = "", before_jump

    if dest not in DEST:
        raise ValueError("line {}: invalid destination: {}".format(line_number, dest))
    if comp not in COMP:
        raise ValueError("line {}: invalid computation: {}".format(line_number, comp))
    if jump not in JUMP:
        raise ValueError("line {}: invalid jump: {}".format(line_number, jump))
    if not comp or (not dest and not jump):
        raise ValueError("line {}: invalid C-instruction: {}".format(
            line_number, instruction
        ))

    return "111" + COMP[comp] + DEST[dest] + JUMP[jump]


def write_symbols(path, labels, symbols):
    with path.open("w", encoding="utf-8", newline="\n") as output:
        output.write("# Labels and variables (predefined symbols omitted)\n")
        for name, address in labels.items():
            output.write("{}={}\n".format(name, address))
        for name, address in symbols.items():
            if name not in labels and name not in predefined_symbols():
                output.write("{}={}\n".format(name, address))


def assemble(input_path):
    instructions = clean_source(input_path)
    symbols = predefined_symbols()
    labels = first_pass(instructions, symbols)
    variables = [16]
    machine_code = []

    for instruction, line_number in instructions:
        if instruction.startswith("("):
            continue
        if instruction.startswith("@"):
            machine_code.append(assemble_a_instruction(
                instruction, line_number, symbols, variables
            ))
        else:
            machine_code.append(assemble_c_instruction(instruction, line_number))

    output_path = input_path.with_suffix(".hack")
    with output_path.open("w", encoding="ascii", newline="\n") as output:
        for machine_instruction in machine_code:
            output.write(machine_instruction + "\n")

    write_symbols(input_path.parent / "symbols.txt", labels, symbols)
    return output_path


def main():
    if len(sys.argv) != 2:
        print("Usage: python assembler.py <input.asm>")
        return 2

    input_path = Path(sys.argv[1])
    if input_path.suffix.lower() != ".asm":
        print("Error: input file must have an .asm extension.")
        return 2
    if not input_path.is_file():
        print("Error: file not found: {}".format(input_path))
        return 2

    try:
        output_path = assemble(input_path)
    except (OSError, UnicodeError, ValueError) as error:
        print("Assembly failed: {}".format(error))
        return 1

    print("Created {}".format(output_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
