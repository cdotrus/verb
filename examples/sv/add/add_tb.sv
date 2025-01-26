// This interface is automatically @generated by Verb.
// It is not intended for manual editing.
interface add_if #(
    parameter integer WORD_SIZE
);
    logic cin;
    logic[WORD_SIZE-1:0] in0;
    logic[WORD_SIZE-1:0] in1;
    logic[WORD_SIZE-1:0] sum;
    logic cout;
endinterface

module add_tb 
    import godan::*;
#(
    parameter integer WORD_SIZE = 16
);

    add_if #(
        .WORD_SIZE(WORD_SIZE)
    ) bfm();

    add_if #(
        .WORD_SIZE(WORD_SIZE)
    ) mdl();

    // instantiate the device under test
    add #(
        .WORD_SIZE(WORD_SIZE)
    ) dut (
        .cin(bfm.cin),
        .in0(bfm.in0),
        .in1(bfm.in1),
        .sum(bfm.sum),
        .cout(bfm.cout)
    );

    logic clk;
    
    // produce a clock with 50% duty cycle
    always #(20ns) clk = ~clk;

    // drive incoming transactions
    always begin: driver 
        int inputs = $fopen("inputs.txt", "r");
        while(!$feof(inputs)) begin
            send(inputs);
            @(negedge clk);
        end
        wait(0);
    end

    // check outgoing transactions for correctness
    always begin: monitor
        int outputs = $fopen("outputs.txt", "r");
        while(!$feof(outputs)) begin
            @(posedge clk);
            recv(outputs);
        end
        $finish;
    end

    // This task is automatically @generated by Verb.
    // It is not intended for manual editing.
    task send(int fd);
        automatic string line;
        if(!$feof(fd)) begin
            $fgets(line, fd);
            `parse(line, bfm.cin);
            `parse(line, bfm.in0);
            `parse(line, bfm.in1);
        end
    endtask

    // This task is automatically @generated by Verb.
    // It is not intended for manual editing.
    task recv(int fd);
        automatic string line;
        if(!$feof(fd)) begin
            $fgets(line, fd);
            `parse(line, mdl.sum);
            `parse(line, mdl.cout);
        end
        `assert_eq(bfm.sum, mdl.sum, "sum");
        `assert_eq(bfm.cout, mdl.cout, "cout");
    endtask

endmodule
