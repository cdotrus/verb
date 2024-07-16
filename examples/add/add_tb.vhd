
library ieee;
use ieee.std_logic_1164.all;

library std;
use std.textio.all;

library amp;
use amp.types.all;

library verb;
use verb.test.all;

entity add_tb is
    generic(
        WORD_SIZE: psize := 16
    );
end entity;

architecture sim of add_tb is

    -- Automatically generated by Verb.
    type add_bfm is record
        cin: logic;
        in0: logics(WORD_SIZE-1 downto 0);
        in1: logics(WORD_SIZE-1 downto 0);
        sum: logics(WORD_SIZE-1 downto 0);
        cout: logic;
    end record;
      
    signal bfm: add_bfm;

    signal clk: logic := '0';
    signal halt: bool := false;
    file events: text open write_mode is "events.log";

begin
    -- instantiate dut
    dut: entity work.add(gp)
        generic map (
            WORD_SIZE => WORD_SIZE
        ) port map (
            cin  => bfm.cin,
            in0  => bfm.in0,
            in1  => bfm.in1,
            sum  => bfm.sum,
            cout => bfm.cout
        );

    --! generate a 50% duty cycle for 25 Mhz
    spin_clock(clk, 40 ns, halt);

    --! test reading a file filled with test vectors
    producer: process
        file inputs: text open read_mode is "inputs.txt";

        -- Automatically generated by Verb.
        procedure send(file fd: text) is
            variable row: line;
        begin
            if endfile(fd) = false then
                readline(fd, row);
                drive(row, bfm.cin);
                drive(row, bfm.in0);
                drive(row, bfm.in1);
            end if;
        end procedure;

    begin  
        -- drive transactions
        while endfile(inputs) = false loop
            send(inputs);
            wait until rising_edge(clk);
        end loop;
        -- wait for all outputs to be checked
        wait;
    end process;

    consumer: process
        file outputs: text open read_mode is "outputs.txt";

        -- Automatically generated by Verb.
        procedure compare(file fd: text) is 
            variable row: line;
            variable expct: add_bfm;
        begin
            if endfile(fd) = false then
                readline(fd, row);
                load(row, expct.sum);
                assert_eq(events, bfm.sum, expct.sum, "sum");
                load(row, expct.cout);
                assert_eq(events, bfm.cout, expct.cout, "cout");
            end if;
        end procedure;

    begin
        while endfile(outputs) = false loop
            -- wait for a valid time to check
            wait until rising_edge(clk);
            -- compare outputs
            compare(outputs);
        end loop;
        -- halt the simulation
        complete(halt);
    end process;

end architecture;