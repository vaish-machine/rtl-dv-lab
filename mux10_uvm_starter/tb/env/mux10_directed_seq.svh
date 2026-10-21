class mux10_directed_seq extends uvm_sequence #(mux10_item);
        `uvm_object_utils(mux10_directed_seq)
        function new(string name = "mux10_directed_seq");
            super.new(name);
        endfunction

        virtual task body();
            mux10_item req;
            for (int combo = 0; combo < 8; combo++) begin
                req = mux10_item::type_id::create($sformatf("directed_%0d", combo));
                start_item(req);
                req.a   = {10{combo[0]}};
                req.b   = {10{combo[1]}};
                req.sel = {10{combo[2]}};
                finish_item(req);
            end
        endtask
    endclass
