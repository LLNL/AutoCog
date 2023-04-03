import asyncio
from autocog import CogArch
from utility import DataSource, IterTextSource
from utility import run_sample, print_results

text   = "T"
texts  = [ "T_1", "T_2" ]
item   = { 'field1' : "F_1", 'field2' : 'F_2' }
items  = [ { 'field1': "F_1_1", 'field2' : 'F_2_1' }, { 'field1': "F_1_2", 'field2' : 'F_2_2' } ]
nested = [ { 'field1': "F_1_1", 'field2' : [ 'F_2_0_1', 'F_2_1_1' ] }, { 'field1': "F_1_2", 'field2' : [ 'F_2_0_2', 'F_2_1_2' ] } ]
dblnsd = [
    { 'field1': "F_1_1", 'field2' : [ { 'subfld' : [ 'F_2_0_1a' , 'F_2_0_1b' ] }, { 'subfld' : [ 'F_2_1_1a' , 'F_2_1_1b' ] } ] },
    { 'field1': "F_1_2", 'field2' : [ { 'subfld' : [ 'F_2_0_2a' , 'F_2_0_2b' ] }, { 'subfld' : [ 'F_2_1_2a' , 'F_2_1_2b' ] } ] }
]

def load_arch():
    arch = CogArch()
    arch.register(DataSource(tag='source-text',      data=text   ))
    arch.register(DataSource(tag='source-list',      data=texts  ))
    arch.register(DataSource(tag='source-item',      data=item   ))
    arch.register(DataSource(tag='source-item-list', data=items  ))
    arch.register(DataSource(tag='source-nested',    data=nested ))
    arch.register(DataSource(tag='source-dblnsd',    data=dblnsd ))

    arch.register(IterTextSource(tag='source-text-iter'))

    arch.load(tag='identity-text-input',          filepath='dataflow/identity-text-input.sta'          )
    arch.load(tag='identity-list-input',          filepath='dataflow/identity-list-input.sta'          )
    arch.load(tag='identity-item-input',          filepath='dataflow/identity-item-input.sta'          )
    arch.load(tag='identity-item-list-input',     filepath='dataflow/identity-item-list-input.sta'     )
    arch.load(tag='identity-nested-input',        filepath='dataflow/identity-nested-input.sta'        )
    arch.load(tag='identity-double-nested-input', filepath='dataflow/identity-double-nested-input.sta' )

    arch.load(tag='identity-text-call',           filepath='dataflow/identity-text-call.sta'          )
    arch.load(tag='identity-list-call',           filepath='dataflow/identity-list-call.sta'          )
    arch.load(tag='identity-item-call',           filepath='dataflow/identity-item-call.sta'          )
    arch.load(tag='identity-item-list-call',      filepath='dataflow/identity-item-list-call.sta'     )
    arch.load(tag='identity-nested-call',         filepath='dataflow/identity-nested-call.sta'        )
    arch.load(tag='identity-double-nested-call',  filepath='dataflow/identity-double-nested-call.sta' )

    arch.load(tag='identity-texts-mapped-input',  filepath='dataflow/identity-texts-mapped-input.sta' )
    arch.load(tag='identity-double-mapped-flow',  filepath='dataflow/identity-double-mapped-flow.sta' )

    arch.load(tag='filter-aggregate-list-text-bool', filepath='dataflow/filter-aggregate-list-text-bool.sta' )

    arch.load(tag='iteration-text-flow', filepath='dataflow/iteration-text-flow.sta' )

    arch.load(tag='iteration-text-call', filepath='dataflow/iteration-text-call.sta' )

    return arch

async def run_tests(arch):
    return await asyncio.gather(
      run_sample(arch, sample='identity-text-input', data=text),
      run_sample(arch, sample='identity-list-input', data=texts),
      run_sample(arch, sample='identity-item-input', data=item),
      run_sample(arch, sample='identity-item-list-input', data=items),
      run_sample(arch, sample='identity-nested-input', data=nested),
      run_sample(arch, sample='identity-double-nested-input', data=dblnsd),

      run_sample(arch, sample='identity-text-call'),
      run_sample(arch, sample='identity-list-call'),
      run_sample(arch, sample='identity-item-call'),
      run_sample(arch, sample='identity-item-list-call'),
      run_sample(arch, sample='identity-nested-call'),
      run_sample(arch, sample='identity-double-nested-call'),

      run_sample(arch, sample='identity-texts-mapped-input', data=texts),
      run_sample(arch, sample='identity-double-mapped-flow', data=texts),

      run_sample(arch, sample='filter-aggregate-list-text-bool', data=["A","B","C","D","E"], keep=[True,False,True,True,False]),

      run_sample(arch, sample='iteration-text-flow', data=text),

      run_sample(arch, sample='iteration-text-call')
    )

if __name__ == '__main__':
    arch = load_arch()
    results = asyncio.run(run_tests(arch))
    print_results(arch, results)