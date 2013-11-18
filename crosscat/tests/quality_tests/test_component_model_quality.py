import crosscat.cython_code.State as State
import crosscat.utils.sample_utils as su
import crosscat.utils.data_utils as du

import crosscat.tests.component_model_extensions.ContinuousComponentModel as ccmext
import crosscat.tests.component_model_extensions.MultinomialComponentModel as mcmext

import random
import pylab
import numpy

default_data_parameters = dict(
    symmetric_dirichlet_discrete=dict(weights=[1.0/5.0]*5),
    normal_inverse_gamma=dict(mu=0.0, rho=1.0)
    )

is_discrete = dict(
    symmetric_dirichlet_discrete=True,
    normal_inverse_gamma=False
    )

def test_one_feature_sampler(component_model_type):
    """
    Tests the ability of component model of component_model_type to capture the
    distribution of the data.
    1. Draws 100 random points from a standard normal distribution
    2. Initializes a component model with that data (and random hyperparameters)
    3. Draws data from that component model
    4. Initialize a crosscat state with that data
    5. Get one sample after 100 transitions
    6. Draw predictive samples
    7. Caluclates the 95 precent support of the continuous distribution or the 
        entire support of the discrete distribution
    8. Calculate the true pdf for each point in the support
    9. Calculate the predictive probability given the sample for each point in
        the support
    10. Plot the original data, predictive samples, pdf, and predictive 
        probabilities
    """
    N = 100
    
    get_next_seed = lambda : random.randrange(2147483647)

    data_params = default_data_parameters[component_model_type.model_type]
    
    X = component_model_type.generate_data_from_parameters(data_params, N, gen_seed=get_next_seed())
    
    hyperparameters = component_model_type.draw_hyperparameters(X)[0]
    
    component_model = component_model_type.from_data(X, hyperparameters)
    
    model_parameters = component_model.sample_parameters_given_hyper()
    
    # generate data from the parameters
    T = component_model_type.generate_data_from_parameters(model_parameters, N, gen_seed=get_next_seed())

    # FIXME:
    # currently there is a bug that causes a freeze when a 1-feature crosscat
    # state is intialized so the below code is so we can test while we wait
    # for the bug fix
    T1 = component_model_type.generate_data_from_parameters(model_parameters, N, gen_seed=get_next_seed())
    T2 = component_model_type.generate_data_from_parameters(model_parameters, N, gen_seed=get_next_seed())
    T1 = numpy.array(T1)
    T2 = numpy.array(T2)
    T = numpy.hstack((T1, T2))
    T = T.tolist()
    # END hack code

    cctypes = [component_model_type.cctype] * 2

    # create a crosscat state 
    M_c = du.gen_M_c_from_T(T, cctypes=cctypes)
    
    state = State.p_State(M_c, T)
    
    # transitions
    state.transition(n_steps=100)
    
    # get the sample
    X_L = state.get_X_L()
    X_D = state.get_X_D()
    
    # generate samples
    predictive_samples = numpy.array(su.simple_predictive_sample(M_c, X_L, X_D, [], [(N,0)], get_next_seed, n=N))
    
    # get support
    discrete_support = component_model_type.generate_discrete_support(model_parameters)

    # calculate simple predictive probability for each point
    Q = [(N,0,x) for x in discrete_support]

    probabilities = su.simple_predictive_probability(M_c, X_L, X_D, []*len(Q), Q,)
    
    T = numpy.array(T)

    # get histogram. Different behavior for discrete and continuous types. For some reason
    # the normed property isn't normalizing the multinomial histogram to 1.
    if is_discrete[component_model_type.model_type]:
        T_hist, edges = numpy.histogram(T[:,0], bins=min(20,len(discrete_support)))
        S_hist, _ =  numpy.histogram(predictive_samples, bins=edges)
        T_hist = T_hist/float(numpy.sum(T_hist))
        S_hist = S_hist/float(numpy.sum(S_hist))
        edges = numpy.array(discrete_support,dtype=float)
    else:
        T_hist, edges = numpy.histogram(T[:,0], bins=min(20,len(discrete_support)), normed=True)
        S_hist, _ =  numpy.histogram(predictive_samples, bins=edges, normed=True)
        edges = edges[0:-1]
    

    # bin widths
    width = (numpy.max(edges)-numpy.min(edges))/len(edges)
    pylab.bar(edges, T_hist, color='blue', alpha=.5, width=width)
    pylab.bar(edges, S_hist, color='red', alpha=.5, width=width)

    # plot actual pdf of support given data params
    pylab.scatter(discrete_support, 
        numpy.exp(component_model_type.log_pdf(numpy.array(discrete_support), 
        model_parameters)), 
        c="blue", 
        s=100, 
        label="true pdf", 
        alpha=1)
            
    # plot predictive probability of support points
    pylab.scatter(discrete_support, 
        numpy.exp(probabilities), 
        c="red", 
        s=100, 
        label="predictive probability", 
        alpha=1)
        
    pylab.legend()

    ylimits = pylab.gca().get_ylim()
    pylab.ylim([0,ylimits[1]])

    pylab.show()

if __name__ == '__main__':
    test_one_feature_sampler(ccmext.p_ContinuousComponentModel)
    test_one_feature_sampler(mcmext.p_MultinomialComponentModel)