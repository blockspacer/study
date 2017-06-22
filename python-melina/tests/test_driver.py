import os
import melina

datadir = os.path.abspath(__file__ + '/../data')

def fromdata(basename):
    return os.path.join(datadir, basename)

class TestDriver():
    def test_nooutput(self, capsys):
        ret = melina.main(args='%s' % fromdata('example.meta'))
        assert ret == melina.EXIT_OK
        assert capsys.readouterr()[1] == 'Your input is beautiful! No output selected though.\n'

    def test_nooutput_fail(self, capsys):
        ret = melina.main(args='%s' % fromdata('configure.xml'))
        assert ret == melina.EXIT_FAILURE
        assert 'unexpected character' in capsys.readouterr()[1]