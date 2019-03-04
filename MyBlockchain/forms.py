from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange



#MINER AND FULL NODE FORMS
class RegisterNodeForm(FlaskForm):
    nodeAddress = StringField('Node Address', validators=[DataRequired()])
    submit1 = SubmitField('Add Node')


class SendToForm(FlaskForm):
    toAddress = StringField('To Public Key Hash', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired()])
    txFee = DecimalField('Transaction Fee', validators=[DataRequired()])
    submit2 = SubmitField('Send Transaction')

class MiningForm(FlaskForm):
    submit3 = SubmitField('Mine!')

class RefreshBalance(FlaskForm):
    submit4 = SubmitField('Refresh')


#QUERY forms
class GetBlockForm(FlaskForm):
    blockNum = IntegerField('Block Number:', validators=[NumberRange(min=1, max=99999999999)])
    submit5 = SubmitField('Search')

class FindTxForm(FlaskForm):
    txHash = StringField('Transaction Hash:', validators=[DataRequired()])
    submit6 = SubmitField('Search')
