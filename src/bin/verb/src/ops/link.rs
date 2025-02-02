use crate::unit::{Language, Net, Unit};
use cliproc::{cli, proc, stage::Memory};
use cliproc::{Arg, Cli, Help, Subcommand};

pub struct Link {
    json: Unit,
    bfm: bool,
    send: bool,
    comp: bool,
    bfm_inst: Option<Vec<String>>,
    // use an 'exclude' list to ignore ports in the bfm
    exclude: Vec<String>,
    list: bool,
}

impl Subcommand<()> for Link {
    fn interpret(cli: &mut Cli<Memory>) -> cli::Result<Self> {
        cli.help(Help::with(HELP))?;
        Ok(Self {
            bfm: cli.check(Arg::flag("if"))?,
            send: cli.check(Arg::flag("send"))?,
            comp: cli.check(Arg::flag("recv"))?,
            list: cli.check(Arg::flag("list"))?,
            bfm_inst: cli.get_all(Arg::option("if-inst").value("name"))?,
            exclude: cli
                .get_all(Arg::option("exclude").switch('x').value("port"))?
                .unwrap_or(Vec::new()),
            json: cli.require(Arg::positional("json"))?,
        })
    }

    fn execute(self, _c: &()) -> proc::Result {
        let filtered_ports: Vec<&Net> = self
            .json
            .get_ports()
            .iter()
            .filter(|p| self.exclude.contains(p.get_identifier()) == false)
            .collect();

        if self.list == true {
            print!("input vectors order:\n ");
            filtered_ports
                .iter()
                .filter(|n| n.is_input())
                .for_each(|n| print!(" {}", n.get_identifier()));
            println!("\n");
            print!("output vectors order:\n ");
            filtered_ports
                .iter()
                .filter(|n| n.is_output())
                .for_each(|n| print!(" {}", n.get_identifier()));
            println!("\n");
            return Ok(());
        }

        let mut space_next_display = false;

        if self.bfm == true {
            let result = match &self.json.get_language() {
                Language::Vhdl => {
                    Self::vhdl_to_string_bfm(&filtered_ports, &self.json.get_identifier())
                }
                Language::SystemVerilog => Self::sv_to_string_bfm(
                    &filtered_ports,
                    self.json.get_generics(),
                    &self.json.get_identifier(),
                ),
                Language::Verilog => todo!(),
            };
            println!("{}", result);
            space_next_display = true;
        }

        if let Some(bfms) = &self.bfm_inst {
            for bfm_inst in bfms {
                if space_next_display == true {
                    println!();
                }
                let result = match &self.json.get_language() {
                    Language::Vhdl => {
                        Self::vhdl_to_string_bfm_inst(&self.json.get_identifier(), bfm_inst)
                    }
                    Language::SystemVerilog => Self::sv_to_string_bfm_inst(
                        &self.json.get_identifier(),
                        &self.json.get_generics(),
                        bfm_inst,
                    ),
                    Language::Verilog => todo!(),
                };
                println!("{}", result);
                space_next_display = true;
            }
        }

        if self.send == true {
            if space_next_display == true {
                println!();
            }
            let filtered_ports: Vec<&Net> = filtered_ports
                .clone()
                .into_iter()
                .filter(|n| n.is_input())
                .collect();

            let result = match &self.json.get_language() {
                Language::Vhdl => Self::vhdl_to_string_send(&filtered_ports, "bfm"),
                Language::SystemVerilog => Self::sv_to_string_send(&filtered_ports, "bfm"),
                Language::Verilog => todo!(),
            };
            println!("{}", result);
            space_next_display = true;
        }

        if self.comp == true {
            if space_next_display == true {
                println!();
            }
            let filtered_ports: Vec<&Net> = filtered_ports
                .into_iter()
                .filter(|n| n.is_output())
                .collect();

            let result = match &self.json.get_language() {
                Language::Vhdl => {
                    Self::vhdl_to_string_comp(&filtered_ports, &self.json.get_identifier(), "bfm")
                }
                Language::SystemVerilog => Self::sv_to_string_comp(
                    &filtered_ports,
                    &self.json.get_identifier(),
                    "bfm",
                    "mdl",
                ),
                Language::Verilog => todo!(),
            };
            println!("{}", result);
            // space_next_display = true;
        }
        Ok(())
    }
}

const HELP: &str = "\
Generate code snippets for hw/sw coherency.

Usage:
    verb link [options] <json>

Args:
    <json>          hw unit's interface encoded in json format

Options:
    --if                  display the hw dut interface
    --if-inst <name>...   display an instance of the hw dut interface
    --send                display the hw function to send inputs to the dut
    --recv                display the hw function to check outputs from the dut
    --exclude, -x <port>... 
                          omit specific ports from the code snippets
    --list                list the port order and exit
";

const VHDL_HEAD_COMMENT: &str = "-- This procedure is automatically @generated by Verb.\n-- It is not intended for manual editing.\n";
const VHDL_HEAD_COMMENT_RECORD: &str = "-- This record is automatically @generated by Verb.\n-- It is not intended for manual editing.\n";

const SV_HEAD_COMMENT: &str = "// This task is automatically @generated by Verb.\n// It is not intended for manual editing.\n";
const SV_HEAD_COMMENT_INTERFACE: &str = "// This interface is automatically @generated by Verb.\n// It is not intended for manual editing.\n";

impl Link {
    fn vhdl_to_string_bfm(ports: &Vec<&Net>, unit: &str) -> String {
        let result = format!(
            "{0}type {1}_if is record\n",
            VHDL_HEAD_COMMENT_RECORD, unit
        );
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{2}{0}: {1};\n",
                n.get_identifier(),
                n.get_type(),
                Self::tab(1)
            ));
            acc
        });
        result.push_str("end record;");
        result
    }

    fn vhdl_to_string_bfm_inst(unit: &str, bfm_inst: &str) -> String {
        let result = format!("signal {}: {}_if;", bfm_inst, unit);
        result
    }
    /*
    // instantiate the set of signals to communicate with the hw dut
    add_bfm #(
        .WORD_SIZE(WORD_SIZE)
    ) bfm();
     */
    fn sv_to_string_bfm_inst(unit: &str, generics: &Vec<Net>, bfm_inst: &str) -> String {
        let result = format!(
            "{0}_if{1} {2}();",
            unit,
            Self::sv_generate_param_inst(generics),
            bfm_inst
        );
        result
    }

    fn sv_generate_param_inst(generics: &Vec<Net>) -> String {
        match generics.len() {
            0 => String::new(),
            _ => {
                let size = generics.len();
                let result = format!(" #(\n");
                let mut result = generics.iter().enumerate().fold(result, |mut acc, (i, n)| {
                    acc.push_str(&format!("{0}.{1}({1})", Self::tab(1), n.get_identifier(),));
                    if i + 1 < size {
                        acc.push(',');
                    }
                    acc.push('\n');
                    acc
                });
                result.push(')');
                result
            }
        }
    }

    fn sv_generate_param_decl(generics: &Vec<Net>) -> String {
        match generics.len() {
            0 => String::new(),
            _ => {
                let size = generics.len();
                let result = format!(" #(\n");
                let mut result = generics.iter().enumerate().fold(result, |mut acc, (i, n)| {
                    acc.push_str(&format!(
                        "{0}{1} {2} {3}",
                        Self::tab(1),
                        n.get_mode(),
                        n.get_type(),
                        n.get_identifier(),
                    ));
                    if i + 1 < size {
                        acc.push(',');
                    }
                    acc.push('\n');
                    acc
                });
                result.push(')');
                result
            }
        }
    }

    fn sv_to_string_bfm(ports: &Vec<&Net>, generics: &Vec<Net>, unit: &str) -> String {
        let result = format!(
            "{0}interface {1}_if{2};\n",
            SV_HEAD_COMMENT_INTERFACE,
            unit,
            Self::sv_generate_param_decl(generics)
        );
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{0}{1} {2};\n",
                Self::tab(1),
                n.get_type(),
                n.get_identifier(),
            ));
            acc
        });
        result.push_str("endinterface");
        result
    }

    fn vhdl_to_string_send(ports: &Vec<&Net>, bfm_inst: &str) -> String {
        let input_fd = "i";
        let drive_fn = "drive";
        let result = format!("{0}procedure send(file {1}: text) is\n{2}variable row: line;\nbegin\n{2}if endfile({1}) = false then\n{3}readline({1}, row);\n", VHDL_HEAD_COMMENT, input_fd, Self::tab(1), Self::tab(2));
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{3}{0}(row, {1}.{2});\n",
                drive_fn,
                bfm_inst,
                n.get_identifier(),
                Self::tab(2),
            ));
            acc
        });
        result.push_str(&format!("{0}end if;\nend procedure;", Self::tab(1)));
        result
    }

    fn sv_to_string_send(ports: &Vec<&Net>, bfm_inst: &str) -> String {
        let input_fd = "fd";
        let drive_fn = "$sscanf(parse";
        let result = format!("{0}task send(int {1});\n{2}automatic string line;\n{2}// Read next set of input values from file\n{2}if(!$feof({1})) begin\n{3}$fgets(line, {1});\n", SV_HEAD_COMMENT, input_fd, Self::tab(1), Self::tab(2));
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{3}{0}(line), \"%b\", {1}.{2});\n",
                drive_fn,
                bfm_inst,
                n.get_identifier(),
                Self::tab(2),
            ));
            acc
        });
        result.push_str(&format!("{0}end\nendtask", Self::tab(1)));
        result
    }

    fn vhdl_to_string_comp(ports: &Vec<&Net>, unit: &str, bfm_inst: &str) -> String {
        let event_fd = "e";
        let output_fd = "o";
        let load_fn = "load";
        let assert_fn = "assert_eq";
        let result = format!("{0}procedure recv(file {1}: text; file {2}: text) is\n{4}variable row: line;\n{4}variable mdl: {3}_bfm;\nbegin\n{4}if endfile({2}) = false then\n{5}readline({2}, row);\n", VHDL_HEAD_COMMENT, event_fd, output_fd, unit, Self::tab(1), Self::tab(2));
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{2}{0}(row, mdl.{1});\n",
                load_fn,
                n.get_identifier(),
                Self::tab(2),
            ));
            acc.push_str(&format!(
                "{4}{3}({0}, {1}.{2}, mdl.{2}, \"{2}\");\n",
                event_fd,
                bfm_inst,
                n.get_identifier(),
                assert_fn,
                Self::tab(2),
            ));
            acc
        });
        result.push_str(&format!("{0}end if;\nend procedure;", Self::tab(1)));
        result
    }

    fn sv_to_string_comp(ports: &Vec<&Net>, _unit: &str, bfm_inst: &str, mdl_inst: &str) -> String {
        let output_fd = "fd";
        let load_fn = "$sscanf(parse";
        let assert_fn = "assert_eq";
        let result = format!("{0}task recv(int {3});\n{1}automatic string line;\n{1}// Read expected output values from file\n{1}if(!$feof({3})) begin\n{2}$fgets(line, {3});\n", SV_HEAD_COMMENT, Self::tab(1), Self::tab(2), output_fd);
        let mut result = ports.iter().fold(result, |mut acc, n| {
            acc.push_str(&format!(
                "{3}{0}(line), \"%b\", {1}.{2});\n",
                load_fn,
                mdl_inst,
                n.get_identifier(),
                Self::tab(2)
            ));
            acc
        });
        result.push_str(&format!("{0}end\n", Self::tab(1)));
        let checks = format!("{0}// Compare received ouputs with expected outputs\n", Self::tab(1));
        let checks = ports.iter().fold(checks, |mut acc, n| {
            acc.push_str(&format!(
                "{1}{2}({3}.{0}, {4}.{0}, \"{0}\");\n",
                n.get_identifier(),
                Self::tab(1),
                assert_fn,
                bfm_inst,
                mdl_inst,
            ));
            acc
        });
        result.push_str(&checks);
        result.push_str(&format!("{0}endtask", Self::tab(0)));
        result
    }

    /// Computes the number of characters required for the longest known
    /// identifier.
    fn _longest_id_len(ids: Vec<&String>) -> usize {
        ids.iter().map(|s| s.len()).max().unwrap_or(0)
    }

    fn tab(n: usize) -> String {
        let spacing = "    ";
        let mut result = String::new();
        for _ in 0..n {
            result.push_str(spacing);
        }
        result
    }
}
