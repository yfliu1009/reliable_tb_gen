from pyosys import libyosys as ys

design = ys.Design()

ys.run_pass("read_verilog ./correct.v", design)
ys.run_pass("prep", design)
ys.run_pass("opt -full", design)

cell_stats = {}
for module in design.selected_whole_modules_warn():
    for cell in module.selected_cells():
        if cell.type.str() in cell_stats:
            cell_stats[cell.type.str()] += 1
        else:
            cell_stats[cell.type.str()] = 1
# plt.bar(range(len(cell_stats)), height = list(cell_stats.values()),align='center')
# plt.xticks(range(len(cell_stats)), list(cell_stats.keys()))
# plt.show()


# # Initialize the Yosys design
# design = pyosys.Design()

# # Create a new Yosys context
# context = pyosys.Context()

# # Example: Load a Verilog file into the design
# verilog_code = """
# module top(input a, b, output y);
#     assign y = a & b;
# endmodule
# """
# context.execute("read_verilog", verilog_code)
# context.execute("hierarchy", "-check", "-top", "top")

# # Inspect the design
# for module in design.modules_:
#     print(f"Module: {module.name}")
